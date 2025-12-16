import time
from app import socketio
import random

from classes.BalanceSheet.index import BalanceSheet
from classes.Bank.index import Bank
from classes.Player.index import Player


def async_apply_and_hire(job_instance, player_instance):
    # random_seconds = random.randint(10, 300)
    time.sleep(5)
    try:
        # Check if the player meets the job's qualification requirements (if such requirements exist)
        job_qualifications = getattr(job_instance, "requirements", [])
        player_qualifications = getattr(player_instance, "qualifications", [])
        balancesheet = BalanceSheet(player=player_instance)
        player_instance.balancesheet = balancesheet

        # Only check qualifications if there are job requirements specified
        if job_qualifications:
            print(f"Job qualifications: {job_qualifications}")
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

        print(f'[DEBUG] Player balacesheet gb applyJob -- {balancesheet.to_dict()}')

        socketio.emit(
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
        # Remove the current player's application from the list if present
        job_instance.applications = [
            a
            for a in job_instance.applications
            if a.get("username") != player_instance.username
        ]
        job_instance.save_to_db()
        socketio.emit(
            "job_application_complete",
            {
                "username": player_instance.username,
                "job_id": str(job_instance._id),
                "error": str(e),
            },
            room=player_instance.username,
        )


def bg_payment(bank: "Bank", player: "Player", amount, recipient):
    try:
        # INSERT_YOUR_CODE
        print(f"[DEBUG] Starting background payment: player={player.username}, amount={amount}, recipient={recipient}")
        bank.make_payment(amount, recipient)
        bank.save_bank_data()
        bs = BalanceSheet(player=player)

        socketio.emit(
            "payment_complete",
            {
                "username": player.username,
                "message": recipient,
                "payload": {"balancesheet": bs.to_dict(), "bank": bank.to_dict()},
            },
            room=player.username,
        )

    except Exception as e:
        # Log if needed
        pass


def bg_update_liability(bs:"BalanceSheet", username, updates, player):
    result = bs.update_liability_in_db(username=username, updates=updates)

    # Refresh balancesheet in-memory after db update

    player.balancesheet = result
    # Avoid triggering another balancesheet save that could overwrite with stale data
    player.save_to_db(skip_balancesheet=True)

    socketio.emit(
        "liabilities_offset_complete",
        {
            "username": player.username,
            "message": 'Liablities updated',
            "payload": {"balancesheet": player.to_dict().get("balancesheet")},
        },
        room=player.username,
    )
