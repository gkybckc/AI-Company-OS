from core.company import Company
from core.agent import Agent


company = Company()

company.hire(
    Agent(
        "Alexander",
        "Executive AI"
    )
)

company.hire(
    Agent(
        "Emily",
        "UI Director"
    )
)

company.hire(
    Agent(
        "David",
        "Backend Architect"
    )
)

company.list_agents()