from aiogram.fsm.state import State, StatesGroup


class TournamentBookingStates(StatesGroup):
    """FSM states representing the Anchor Wizard tournament booking flow."""
    waiting_title = State()       # Tournament title input
    selecting_date = State()      # Slot picker interactive calendar grid
    selecting_format = State()    # Format chips (online/lan, bracket, roster)
    waiting_rulebook = State()    # Document file or Google Drive/Docs URL
    confirm_booking = State()     # Final summary review card
