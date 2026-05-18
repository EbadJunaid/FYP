
class OverviewSerializer:
    @staticmethod
    def serialize_overview(summary=None, trends=None):
        return {
            "summary": summary,
            "trends": trends,
        }
