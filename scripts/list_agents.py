"""List all agents with their status from AGENTS.yaml."""

from holus.agents.registry import AgentRegistry

reg = AgentRegistry()
all_agents = reg.list_agents()

h_id, h_type, h_status, h_model = "ID", "TYPE", "STATUS", "MODEL"
print(f"{h_id:<35} {h_type:<12} {h_status:<10} {h_model:<16} VERSION")
print("-" * 90)
for a in sorted(all_agents, key=lambda x: (x.type, x.agent_id)):
    print(f"{a.agent_id:<35} {a.type:<12} {a.status:<10} {a.model_tier:<16} {a.version}")
print()
active = sum(1 for a in all_agents if a.status == "active")
planned = sum(1 for a in all_agents if a.status == "planned")
print(f"Total: {len(all_agents)} agents  (active: {active}  planned: {planned})")
