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
        self.id = ""
        self.message_id = ""
        self.notes = ""
        self.post_date = ""
