from abc import ABC, abstractmethod

class BasePaymentGateway(ABC):
    @abstractmethod
    def initiate_payment(self, order):
        pass

    @abstractmethod
    def verify_payment(self, payment, **kwargs):
        pass
