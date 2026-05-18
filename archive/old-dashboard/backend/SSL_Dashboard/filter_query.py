from .Date_helper import date_helper

class Filter:
    def __init__(self):
        self.date=date_helper()
        # pass

    def filter_status(self, status=None,filter_status=None):

        # Status filter
        if filter_status is None:
            filter_status = {}
         
        if status == "active":
            filter_status["parsed.validity.end"] = {"$gte": self.date._now_iso()}
        elif status == "expired":
            filter_status["parsed.validity.end"] = {"$lt": self.date._now_iso()}
        elif status == "expiring_soon":
            filter_status["parsed.validity.end"] = {"$gte": self.date._now_iso(), "$lte": self.date._soon_iso()}

        return filter_status


    def filter_issuer(self,issuer=None,filter_issuer =None):
        if filter_issuer is None:
            filter_issuer = {}
         # Issuer filter
        if issuer:
            filter_issuer["parsed.issuer.organization.0"] = issuer

        return filter_issuer

    def filter_country(self,country=None,filter_country=None):
        if filter_country is None:
            filter_country={}
        # Country filter
        if country:
            filter_country["parsed.subject.country.0"] = country

        return filter_country

    def filter_validation_level(self,validation_level=None,filter_validation=None):
        
         # Validation Level filter
        if filter_validation is None:
            filter_validation={}

        if validation_level:
            filter_validation["parsed.validation_level"] = validation_level

        return filter_validation
    

    def _build_base_filter(self, status=None, issuer=None, country=None, validation_level=None):
        filter_query = {}

        filter_query= self.filter_status(status,filter_query)
        filter_query=self.filter_issuer(issuer,filter_query)
        filter_query=self.filter_country(country,filter_query)
        
        filter_query=self.filter_validation_level(validation_level,filter_query)
       
        return filter_query
