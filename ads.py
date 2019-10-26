import uuid

class Ads(object):
    def __init__(self, user):
        self.user = user
        self.type = None
        self.region = ""
        self.brand = ""
        self.shoe_name = ""
        self.number = -1
        self.condition = ""
        self.price = -1
        self.availability = ""
        self.shipping = False
        self.accept_paypal = False
        self.photo = ""
        self.id = str(uuid.uuid4())
        self.message_id = ""
        self.notes = ""
