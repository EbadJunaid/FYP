from django.db import models

# Create your models here.
# backend/certificates/models.py
# Pure Python representation of our SSL Certificate Model
class SSLCertificateModel:
    def __init__(self, domain, issuer, expiry_date):
        self.domain = domain
        self.issuer = issuer
        self.expiry_date = expiry_date

    def to_dict(self):
        return {
            "domain": self.domain,
            "issuer": self.issuer,
            "expiry_date": self.expiry_date
        }