
class FakeStripeMetadata(dict):
    def to_dict(self):
        return dict(self)