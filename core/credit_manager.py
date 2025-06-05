#core/credit_manager.py# video_jukebox/core/credit_manager.py
import logging
logger = logging.getLogger("VideoJukebox.CreditManager") # Get a child logger

class CreditManager:
    def __init__(self, settings_manager, initial_credits=0):
        self.settings_manager = settings_manager
        self._balance = initial_credits
        logger.info(f"Initialized with {self._balance} credits.")        
        # In a real system, credits might be loaded from a persistent store
        # or linked to a payment system. For now, it's in-memory.
        logger.info(f"Initialized with {self._balance} credits.")

    def add_credits(self, amount):
        if amount > 0:
            self._balance += amount
            logger.info(f"Added {amount} credits. New balance: {self._balance}")
            return True
        logger.warning(f"Invalid amount to add: {amount}")
        return False

    def deduct_credits(self, amount):
        if amount > 0 and self._balance >= amount:
            self._balance -= amount
            logger.info(f"Deducted {amount} credits. New balance: {self._balance}")
            return True
        elif amount <= 0:
            logger.warning(f"Invalid amount to deduct: {amount}")
        else:
            logger.warning(f"Insufficient credits. Balance: {self._balance}, Tried to deduct: {amount}")
        return False

    def get_balance(self):
        return self._balance

    def can_afford(self, cost):
        return self._balance >= cost

    def set_balance(self, amount):
        """ Direct way to set balance, e.g., for management override or loading state """
        if amount >= 0:
            self._balance = amount
            logger.info(f"Balance directly set to: {self._balance}")
        else:
            logger.info(f"Cannot set balance to a negative amount: {amount}")