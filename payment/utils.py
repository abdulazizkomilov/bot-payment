import logging
from datetime import datetime, timedelta
from core.settings import users_collection


def update_user_payment(user_id: int, amount: int):
    payment_date = datetime.now()

    if amount == 45000:
        payment_valid_date = payment_date + timedelta(days=30)
    elif amount == 10000:
        payment_valid_date = payment_date + timedelta(weeks=1)
    else:
        logging.error(f"Xato: {amount} so‘m to‘lov summasi noto‘g‘ri!")
        return

    filter_query = {"_id": user_id}
    update_data = {
        "$set": {
            "is_paid": True,
            "payment_date": payment_date,
            "payment_valid_date": payment_valid_date,
        }
    }

    result = users_collection.update_one(filter_query, update_data)

    if result.matched_count:
        logging.info(f"User {user_id} muvaffaqiyatli to‘ldirildi.")
    else:
        logging.error(f"User {user_id} topilmadi.")
