# INSERT_YOUR_CODE

from classes.Player.index import Player
from datetime import datetime


def mock_balancesheet_for_working_class(username="player1"):
    """
    Returns a BalanceSheet instance with representative assets, liabilities,
    income, and expenses for a regular working class citizen.
    """

    assets = [
        {"name": "Checking Account", "income": 0, "value": 2500},
        {"name": "Savings Account", "income": 0.5, "value": 1500},
        {"name": "Used Car", "income": 0, "value": 5000},
        {"name": "Household Goods", "income": 0, "value": 800},
    ]

    liabilities = [
        {
            "name": "Car Loan",
            "loanAmount": 45000,
            "originalLoanAmount": 48000,
            "interestRate": 0.05,
            "amortizationTerm": 60,  # months, example value
            "compoundingFrequency": "weekly",
            "paymentFrequency": "monthly",
            "totalPaymentsMade": 10,
            "totalAmountPaid": 8000,
            "startDate": "2023-01-01",
            "durationMonths": 60,
            "nextDueDate": "2024-07-01"
        },
        {
            "name": "Credit Card Debt",
            "loanAmount": 1200,
            "originalLoanAmount": 3500,
            "interestRate": 0.18,
            "amortizationTerm": 24,  # months, example value
            "compoundingFrequency": "monthly",
            "paymentFrequency": "monthly",
            "totalPaymentsMade": 8,
            "totalAmountPaid": 2300,
            "startDate": "2023-11-01",
            "durationMonths": 24,
            "nextDueDate": "2024-07-15"
        },
        {
            "name": "House Mortgage Debt",
            "loanAmount": 220000,
            "originalLoanAmount": 489200,
            "interestRate": 0.04,
            "amortizationTerm": 360,  # months, example value (30 years)
            "compoundingFrequency": "monthly",
            "paymentFrequency": "monthly",
            "totalPaymentsMade": 18,
            "totalAmountPaid": 45000,
            "startDate": "2022-01-01",
            "durationMonths": 360,
            "nextDueDate": "2024-07-01"
        }
    ]

    expenses = [
        
    ]

    bs = Player(username).get_player(username).balancesheet

    for asset in assets:
        bs.add_asset(asset["name"], asset["income"],asset["value"], username)
    for liability in liabilities:
        bs.add_liability(
            liability["name"],
            liability["loanAmount"],
            liability["interestRate"],
            amortizationTerm=liability.get("amortizationTerm"),
            compoundingFrequency=liability.get("compoundingFrequency"),
            paymentFrequency=liability.get("paymentFrequency"),
            totalPaymentsMade=liability.get("totalPaymentsMade"),
            totalAmountPaid=liability.get("totalAmountPaid"),
            startDate=liability.get("startDate"),
            durationMonths=liability.get("durationMonths"),
            nextDueDate=liability.get("nextDueDate"),
            originalLoanAmount=liability.get("originalLoanAmount"),
            username=username
        )
    
    bs.assets = assets
    bs.liabilities = liabilities
    # bs.save_to_db(username)
    return bs


