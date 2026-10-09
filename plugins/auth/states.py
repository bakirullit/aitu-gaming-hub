from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    """FSM states for user registration and identity verification."""
    choose_role = State()
    waiting_full_name = State()
    waiting_phone = State()
    waiting_gmail = State()
    waiting_barcode = State()
    waiting_otp = State()
    waiting_steam = State()
