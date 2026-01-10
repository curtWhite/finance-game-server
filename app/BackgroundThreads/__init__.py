"""
Background thread functions for async operations.
These functions are designed to work with Flask-SocketIO and Gunicorn gthread workers.

When using threading mode, background tasks use standard Python threading.Thread
for proper async handling with Flask-SocketIO.
"""

import time
from app import socketio, app
import logging

from classes.BalanceSheet.index import BalanceSheet
from classes.Bank.index import Bank
from classes.Player.index import Player
from classes.Lotto.index import Lotto


# Set up logging
logger = logging.getLogger(__name__)


def _emit_to_room(socketio_instance, event, data, room, namespace=None):
    """
    Safely emit a socket event to a room, with error handling.

    Args:
        socketio_instance: The SocketIO instance
        event: Event name
        data: Event data
        room: Room name (typically username)
        namespace: Optional namespace
    """
    try:
        # Check if room exists and has connected clients
        # Note: This works with threading mode for Flask-SocketIO
        socketio_instance.emit(
            event, data, room=room, namespace=namespace, callback=None
        )
        logger.info(
            f"Emitted '{event}' to room '{room}' for user '{data.get('username', 'unknown')}'"
        )
    except Exception as e:
        logger.error(f"Failed to emit '{event}' to room '{room}': {str(e)}")
        # Still try to emit without room (broadcast) as fallback if room doesn't exist
        try:
            socketio_instance.emit(
                event,
                {
                    **data,
                    "room_error": f"Room '{room}' may not exist, broadcasting instead",
                },
                namespace=namespace,
            )
        except Exception as broadcast_error:
            logger.error(f"Failed to broadcast '{event}': {str(broadcast_error)}")


def async_apply_and_hire(job_instance, player_instance):
    """
    Background task to process job application and hiring.
    This function runs in a background thread/task and emits SocketIO events when complete.

    Args:
        job_instance: Job instance to apply for
        player_instance: Player instance applying for the job
    """
    # random_seconds = random.randint(10, 300)
    time.sleep(5)

    # Ensure we have Flask application context for database operations
    with app.app_context():
        try:
            # Check if the player meets the job's qualification requirements (if such requirements exist)
            job_qualifications = getattr(job_instance, "requirements", [])
            player_qualifications = getattr(player_instance, "qualifications", [])
            balancesheet = BalanceSheet(player=player_instance)
            player_instance.balancesheet = balancesheet

            # Only check qualifications if there are job requirements specified
            if job_qualifications:
                logger.info(f"Job qualifications: {job_qualifications}")
                # Each required qualification must be in the player's qualifications list
                missing_qualifications = [
                    q
                    for q in job_qualifications
                    if q not in player_qualifications and q not in ["None", None]
                ]
                if missing_qualifications:
                    raise ValueError(
                        f"Player '{player_instance.username}' does not meet the following qualification requirements for this job: {missing_qualifications}"
                    )

            job_instance.hire(player_instance)

            logger.info(
                f"[DEBUG] Player balancesheet after applyJob -- {balancesheet.to_dict()}"
            )

            # Emit success event to the player's room
            _emit_to_room(
                socketio,
                "job_application_complete",
                {
                    "username": player_instance.username,
                    "job_id": str(job_instance._id),
                    "message": f"Job application process for '{job_instance.title}' at '{job_instance.company}' complete.",
                    "payload": {
                        "job": job_instance.to_dict(),
                        "time_slots": player_instance.time_slots,
                        "balancesheet": balancesheet.to_dict(),
                    },
                },
                room=player_instance.username,
            )
        except Exception as e:
            logger.error(
                f"Error processing job application for {player_instance.username}: {str(e)}"
            )
            # Remove the current player's application from the list if present
            try:
                job_instance.applications = [
                    a
                    for a in job_instance.applications
                    if a.get("username") != player_instance.username
                ]
                job_instance.save_to_db()
            except Exception as save_error:
                logger.error(f"Failed to clean up job application: {str(save_error)}")

            # Emit error event to the player's room
            _emit_to_room(
                socketio,
                "job_application_complete",
                {
                    "username": player_instance.username,
                    "job_id": str(job_instance._id),
                    "error": str(e),
                    "success": False,
                },
                room=player_instance.username,
            )


def bg_payment(bank: "Bank", player: "Player", amount, recipient, late_payment):
    """
    Background task to process bank payments.
    This function runs in a background thread/task and emits SocketIO events when complete.

    Args:
        bank: Bank instance
        player: Player instance making the payment
        amount: Payment amount
        recipient: Payment recipient
    """
    # Ensure we have Flask application context for database operations
    with app.app_context():
        try:
            logger.info(
                f"[DEBUG] Starting background payment: player={player.username}, amount={amount}, recipient={recipient}"
            )
            bank.make_payment(amount, recipient, late_payment)
            bank.save_bank_data()
            bs = BalanceSheet(player=player)

            # Emit success event to the player's room
            _emit_to_room(
                socketio,
                "payment_complete",
                {
                    "username": player.username,
                    "message": f"Payment of {amount} to {recipient} completed successfully",
                    "payload": {
                        "balancesheet": bs.to_dict(),
                        "bank": bank.to_dict(),
                    },
                },
                room=player.username,
            )
            logger.info(f"Payment completed successfully for {player.username}")

        except ValueError as e:
            # Business logic errors (e.g., insufficient funds)
            logger.warning(f"Payment failed for {player.username}: {str(e)}")
            _emit_to_room(
                socketio,
                "payment_complete",
                {
                    "username": player.username,
                    "error": str(e),
                    "success": False,
                    "message": f"Payment failed: {str(e)}",
                },
                room=player.username,
            )
        except Exception as e:
            # Unexpected errors
            logger.error(
                f"Unexpected error processing payment for {player.username}: {str(e)}",
                exc_info=True,
            )
            _emit_to_room(
                socketio,
                "payment_complete",
                {
                    "username": player.username,
                    "error": "An unexpected error occurred while processing the payment",
                    "success": False,
                    "message": "Payment processing failed due to a server error",
                },
                room=player.username,
            )


def bg_update_liability(bs: "BalanceSheet", username, updates, player):
    """
    Background task to update liabilities in the balance sheet.
    This function runs in a background thread/task and emits SocketIO events when complete.

    Args:
        bs: BalanceSheet instance
        username: Username of the player
        updates: List of liability updates
        player: Player instance
    """
    # Ensure we have Flask application context for database operations
    with app.app_context():
        try:
            logger.info(f"Updating liabilities for {username}")
            result = bs.update_liability_in_db(username=username, updates=updates)

            # Refresh balancesheet in-memory after db update
            player.balancesheet = result
            # Avoid triggering another balancesheet save that could overwrite with stale data
            player.save_to_db(skip_balancesheet=True)

            # Emit success event to the player's room
            _emit_to_room(
                socketio,
                "liabilities_offset_complete",
                {
                    "username": player.username,
                    "message": "Liabilities updated successfully",
                    "payload": {"balancesheet": player.to_dict().get("balancesheet")},
                },
                room=player.username,
            )
            logger.info(f"Liabilities updated successfully for {username}")

        except Exception as e:
            logger.error(
                f"Error updating liabilities for {username}: {str(e)}", exc_info=True
            )
            _emit_to_room(
                socketio,
                "liabilities_offset_complete",
                {
                    "username": player.username,
                    "error": str(e),
                    "success": False,
                    "message": "Failed to update liabilities",
                },
                room=player.username,
            )


# Use threading.Thread for background asset update (for consistency with liabilities)
def bg_update_asset(bs:"BalanceSheet", username, updates, player):
    with app.app_context():
        try:
            bs.update_assets_in_db(username=username, updates=updates)
            player.balancesheet = bs
            player.save_to_db(skip_balancesheet=True)


            _emit_to_room(
                socketio,
                "assets_update_complete",
                {
                    "username": player.username,
                    "message": "Assets updated successfully",
                    "payload": {"balancesheet": player.to_dict().get("balancesheet")},
                },
                room=player.username,
            )
        except Exception as e:
            # Optionally log or emit failure event
            logging.exception("Error updating assets for user %s: %s", username, str(e))
            
            _emit_to_room(
                socketio,
                "assets_update_complete",
                {
                    "username": player.username,
                    "error": str(e),
                    "success": False,
                    "message": "Failed to update assets",
                },
                room=player.username,
            )
            pass




def bg_salary_confirmation(bank, player: "Player", amount, proxy, message):
    with app.app_context():
        new_player = player.load_from_db(player.username)
        try:
            _emit_to_room(
                socketio,
                "salary_reciept_complete",
                {
                    "username": player.username,
                    "message": message,
                    "payload": {"player": new_player.to_dict()},
                },
                room=player.username,
            )
        except Exception as e:
            logger.error(f"Error paying salary for {player.username}: {str(e)}")


def update_properties_in_background(player, Property, property_ids, years, update_balancesheet):
    """
    Runs in a background thread. Applies appreciation to user-owned properties.
    This implementation is synchronous because background threads are already asynchronous
    with respect to the Flask process, and use of asyncio here would add unnecessary complexity.
    """
    try:
        print('************************** UPDATING PROPERTY VALUE **************************************')
        # Fetch all properties owned by the player
        prop_instance = Property(player)
        owned_props = prop_instance.load_all_owned_properties()
        # Build a map for fast lookup
        owned_props_map = {str(prop.get("id")): prop for prop in owned_props}
        for pid in property_ids:
            prop_data = owned_props_map.get(str(pid))
            if not prop_data:
                continue  # Skip properties not found
            target_property = Property(player)
            target_property.from_dict(prop_data)
            # Set the property _id properly
            if prop_data.get("id"):
                target_property._id = prop_data["id"]
            else:
                target_property._id = pid
            try:
                target_property.apply_appreciation(years=years, update_balancesheet=update_balancesheet)
                target_property.save_to_db()
            except Exception as e:
                print(f"Failed to apply appreciation for property id {pid}: {e}")

    except Exception as e:
        print(f"Exception in update_properties_in_background: {e}")


def bg_process_lotto_ticket(lotto_ticket: "Lotto", player: "Player", delay_seconds=None):
    """
    Background task to process a lotto ticket after the delay period.
    This function runs in a background thread/task and emits SocketIO events when complete.
    
    Args:
        lotto_ticket: Lotto ticket instance to process
        player: Player instance who owns the ticket
        delay_seconds: Optional delay in seconds (if None, calculates from ticket.result_at)
    """
    # Calculate wait time
    if delay_seconds is None:
        if lotto_ticket.result_at:
            from datetime import datetime
            now = datetime.utcnow()
            result_time = lotto_ticket.result_at
            if isinstance(result_time, str):
                # Parse ISO format string
                try:
                    # Try Python 3.7+ fromisoformat
                    result_time = datetime.fromisoformat(result_time.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # Fallback for older Python versions or different formats
                    try:
                        result_time = datetime.strptime(result_time.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                    except ValueError:
                        result_time = datetime.strptime(result_time.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
            elif not isinstance(result_time, datetime):
                # If it's not a datetime object, default to 1 hour
                wait_seconds = 3600
                result_time = None
            else:
                result_time = result_time
            
            if result_time:
                wait_seconds = max(0, (result_time - now).total_seconds())
            else:
                wait_seconds = 3600
        else:
            # Default to 1 hour if no result_at set
            wait_seconds = 3600
    else:
        wait_seconds = delay_seconds
    
    # Wait for the delay period
    if wait_seconds > 0:
        logger.info(f"Waiting {wait_seconds} seconds before processing lotto ticket for {player.username}")
        time.sleep(wait_seconds)
    
    # Ensure we have Flask application context for database operations
    with app.app_context():
        try:
            logger.info(
                f"Processing lotto ticket for player {player.username}, ticket_id: {lotto_ticket._id}"
            )
            
            # Reload ticket from DB to ensure we have latest data
            ticket = Lotto.load_from_db(lotto_ticket._id, player=player)
            if not ticket:
                raise ValueError(f"Ticket {lotto_ticket._id} not found")
            
            # Check if ticket is ready to be processed
            if ticket.status != "pending":
                logger.warning(f"Ticket {ticket._id} is not pending (status: {ticket.status})")
                return
            
            # Process the ticket (check winning condition)
            result = ticket.check_winning_condition()
            
            # If player won, add prize to their bank account
            bank = None
            if result["status"] == "won" and result["prize_amount"] > 0:
                from classes.Bank.index import Bank
                bank = Bank(customer=player)
                bank.load_bank_data()
                bank.deposit(
                    amount=result["prize_amount"],
                    sender="Lotto Office",
                    message=f"Lotto prize for ticket {str(ticket._id)}"
                )
                logger.info(
                    f"Prize of {result['prize_amount']} deposited to {player.username}'s bank account"
                )
            
            # Reload player to get updated balancesheet
            updated_player = Player.load_from_db(player.username)
            balancesheet = BalanceSheet(player=updated_player)
            
            # Emit success event to the player's room
            _emit_to_room(
                socketio,
                "lotto_result_ready",
                {
                    "username": player.username,
                    "ticket_id": str(ticket._id),
                    "message": "Lotto ticket result is ready!",
                    "payload": {
                        "ticket": ticket.to_dict(),
                        "result": result,
                        "balancesheet": balancesheet.to_dict(),
                        "bank": bank.to_dict() if bank else None,
                    },
                },
                room=player.username,
            )
            logger.info(f"Lotto ticket processed successfully for {player.username}")
            
        except Exception as e:
            logger.error(
                f"Error processing lotto ticket for {player.username}: {str(e)}",
                exc_info=True,
            )
            # Emit error event to the player's room
            _emit_to_room(
                socketio,
                "lotto_result_ready",
                {
                    "username": player.username,
                    "ticket_id": str(lotto_ticket._id) if lotto_ticket._id else None,
                    "error": str(e),
                    "success": False,
                    "message": "Failed to process lotto ticket",
                },
                room=player.username,
            )