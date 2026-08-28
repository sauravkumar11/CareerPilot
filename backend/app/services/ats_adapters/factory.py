from app.domain.models.job import ATSProvider
from app.services.ats_adapters.ashby import AshbyAdapter
from app.services.ats_adapters.base import BaseATSAdapter
from app.services.ats_adapters.greenhouse import GreenhouseAdapter
from app.services.ats_adapters.lever import LeverAdapter
from app.services.ats_adapters.smartrecruiters import SmartRecruitersAdapter

_ADAPTER_REGISTRY: dict[ATSProvider, type[BaseATSAdapter]] = {
    ATSProvider.GREENHOUSE: GreenhouseAdapter,
    ATSProvider.LEVER: LeverAdapter,
    ATSProvider.ASHBY: AshbyAdapter,
    ATSProvider.SMARTRECRUITERS: SmartRecruitersAdapter,
}


def get_adapter(provider: ATSProvider) -> BaseATSAdapter:
    adapter_cls = _ADAPTER_REGISTRY.get(provider)
    if adapter_cls is None:
        raise ValueError(
            f"No adapter registered for {provider}. Supported providers: {list(_ADAPTER_REGISTRY.keys())}"
        )
    return adapter_cls()
