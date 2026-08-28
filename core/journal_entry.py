from dataclasses import dataclass


@dataclass
class JournalEntry:
    account_id: int | str
    quantity: float
    amount: float
    unit_price: float = 1.0

    def to_json(self) -> dict:
        return {
            "account": self.account_id,
            "quantity": self.quantity,
            "amount": self.amount,
            "unit_price": self.unit_price,
        }
