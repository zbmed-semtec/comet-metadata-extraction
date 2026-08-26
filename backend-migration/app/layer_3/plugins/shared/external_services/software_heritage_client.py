from app.layer_3.plugins.shared.foundation.caching_http_client import CachingHttpClient
from app.layer_3.steps.contracts import ExtractionState, ExtractionContext

class SoftwareHeritageClient(CachingHttpClient):
    
    name = 'de.zbmed.sofware.heritage.client'

    def __init__(self, context: ExtractionContext, state: ExtractionState):
        super().__init__(context, state)

    def get_archive_url(self):
        archive_url = f"https://archive.softwareheritage.org/browse/origin/directory/?origin_url={self.context.repo_url}"
        try:
            res = self._caching_get(archive_url)
            if res.ok:
                return archive_url
            return None
        except:
            return None
    
    def _build_headers(self):
        return {}