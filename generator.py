#!/usr/bin/env python3
'''
generate_synthetic_kpis.py
Libraries: pandas numpy faker textblob
'''
from faker import Faker
import pandas as pd
import numpy as np
from datetime import timedelta
import random

try:
    from textblob import TextBlob
    def sentiment_score(text):
        return round(TextBlob(text).sentiment.polarity, 3)  # -1..1
except Exception:
    # fallback simple keyword-based polarity -1..1
    def sentiment_score(text):
        text = (text or "").lower()
        pos = sum(text.count(w) for w in ["good","great","excellent","happy","love","satisfied","fast","easy"])
        neg = sum(text.count(w) for w in ["bad","terrible","slow","hate","angry","frustrat","poor","delay","problem"])
        if pos+neg == 0:
            return 0.0
        return round((pos-neg) / (pos+neg), 3)

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

N = 10000
rows = []

channels = ['email','phone','chat','social']
issues = ['billing','technical','account','shipping','other']
priorities = ['low','medium','high','urgent']
sla_map = {'low':72,'medium':48,'high':24,'urgent':4}
products = [f"prod_{i:03d}" for i in range(1,51)]
regions = ['NA','EU','APAC','LATAM','MEA']
agent_skill_levels = ['junior','mid','senior']

# scenarios to create varied operational conditions
scenarios = [
    "baseline",
    "product_outage",
    "marketing_campaign",
    "holiday_weekend",
    "vip_wave",
    "bot_failure",
    "refund_spike",
    "regional_outage"
]
scenario_weights = [0.6, 0.02, 0.08, 0.06, 0.03, 0.05, 0.03, 0.03]

# define VIP customers set
vip_customers = {f"C{cid:06d}" for cid in np.random.choice(range(1,5000), size=50, replace=False)}

timezone_map = {'NA':'America/New_York','EU':'Europe/Berlin','APAC':'Asia/Singapore','LATAM':'America/Sao_Paulo','MEA':'Africa/Johannesburg'}

for i in range(N):
    ticket_id = f"T{i+1:07d}"
    customer_id = f"C{np.random.randint(1,5000):06d}"
    created = fake.date_time_between(start_date='-90d', end_date='now')
    channel = np.random.choice(channels, p=[0.4,0.2,0.3,0.1])
    issue = np.random.choice(issues, p=[0.15,0.4,0.2,0.1,0.15])
    priority = np.random.choice(priorities, p=[0.4,0.35,0.2,0.05])
    sla = sla_map[priority]
    product_id = random.choice(products)
    region = random.choice(regions)
    timezone = timezone_map[region]
    agent_id = f"A{np.random.randint(1,800):05d}"
    agent_tenure_days = int(abs(np.random.normal(loc=540, scale=400)))
    agent_skill = np.random.choice(agent_skill_levels, p=[0.35,0.45,0.2])
    customer_tenure_days = max(0, int(np.random.exponential(scale=400)))
    customer_segment = np.random.choice(['free','basic','premium','enterprise'], p=[0.25,0.45,0.25,0.05])

    # scenario selection
    scenario = np.random.choice(scenarios, p=scenario_weights)
    num_contacts_extra = 0

    # base load factors
    hour = created.hour
    weekday = created.weekday()  # 0=Mon
    hour_load_factor = 1.2 if 9 <= hour <= 17 else 0.8
    day_load_factor = 1.1 if weekday < 5 else 0.7

    # apply scenario-level overrides
    if scenario == "product_outage":
        if np.random.rand() < 0.7:
            issue = 'technical'
            priority = np.random.choice(['high','urgent'], p=[0.6,0.4])
            sla = sla_map[priority]
            product_id = random.choice(products[:5])
    elif scenario == "marketing_campaign":
        if np.random.rand() < 0.7:
            product_id = random.choice(products[10:20])
            issue = np.random.choice(['billing','account'], p=[0.6,0.4])
            channel = np.random.choice(channels, p=[0.55,0.15,0.2,0.1])
    elif scenario == "holiday_weekend":
        if np.random.rand() < 0.8:
            # force weekend creation
            created = fake.date_time_between(start_date='-30d', end_date='now')
            while created.weekday() < 5:
                created = fake.date_time_between(start_date='-30d', end_date='now')
            hour = created.hour
            weekday = created.weekday()
            hour_load_factor *= 1.3
            day_load_factor *= 0.6
            channel = np.random.choice(channels, p=[0.5,0.05,0.25,0.2])
    elif scenario == "vip_wave":
        if customer_id in vip_customers or np.random.rand() < 0.01:
            customer_segment = 'enterprise'
            priority = np.random.choice(['high','urgent','medium'], p=[0.5,0.3,0.2])
            sla = sla_map[priority]
            agent_skill = np.random.choice(['mid','senior'], p=[0.3,0.7])
    elif scenario == "bot_failure":
        if np.random.rand() < 0.6:
            channel = np.random.choice(channels, p=[0.45,0.25,0.15,0.15])
            num_contacts_extra = np.random.poisson(1)
    elif scenario == "refund_spike":
        if np.random.rand() < 0.7:
            issue = 'billing'
            priority = np.random.choice(['medium','high'], p=[0.6,0.4])
            sla = sla_map[priority]
    elif scenario == "regional_outage":
        affected = np.random.choice(['NA','EU','APAC'])
        if region == affected or np.random.rand() < 0.6:
            region = affected
            timezone = timezone_map[region]
            if np.random.rand() < 0.7:
                issue = 'technical'

    # response delay in hours (channel & load effect)
    base_resp = {'chat':0.5,'phone':0.25,'email':8,'social':6}[channel]
    resp_jitter = np.random.exponential(scale=base_resp * hour_load_factor * day_load_factor)
    # VIP faster handling
    if scenario == "vip_wave" and customer_segment == 'enterprise':
        resp_jitter *= 0.5

    first_resp = created + pd.Timedelta(hours=resp_jitter)

    # wait_time_minutes
    if channel in ('phone','chat'):
        wait_minutes = max(0, np.random.normal(loc=5*hour_load_factor*day_load_factor, scale=3))
        if scenario == "holiday_weekend":
            wait_minutes += max(0, np.random.normal(5,3))
        if scenario == "vip_wave" and customer_segment == 'enterprise':
            wait_minutes = max(0, wait_minutes * 0.4)
    else:
        wait_minutes = 0.0
    wait_minutes = round(wait_minutes, 1)

    # resolution delay hours dependent on issue complexity and priority
    complexity = {'technical':1.6,'billing':1.0,'account':0.9,'shipping':1.1,'other':0.95}[issue]
    base_res = np.random.gamma(shape=2, scale=8) * complexity * (1.0 if priority!='urgent' else 0.6)
    # product outage or regional outage increases resolution/time and escalations
    if scenario in ("product_outage","regional_outage") and np.random.rand() < 0.6:
        base_res *= np.random.uniform(1.5,3.0)
    closed = created + pd.Timedelta(hours=base_res)

    # num_contacts
    num_contacts = 1 + np.random.poisson(lam=0.25*complexity) + num_contacts_extra
    escalation = base_res > (24 * complexity)
    # bump escalation for outages
    if scenario in ("product_outage","regional_outage") and np.random.rand() < 0.5:
        escalation = True
    reopen = np.random.rand() < (0.02 if not escalation else 0.08)
    if scenario in ("product_outage","regional_outage"):
        reopen = np.random.rand() < 0.12
    resolution = np.random.choice(['solved','workaround','refunded','escalated'],
                                  p=[0.7,0.18,0.05,0.07])
    if escalation:
        resolution = 'escalated'
    if scenario == "refund_spike" and np.random.rand() < 0.6:
        resolution = np.random.choice(['refunded','workaround','solved'], p=[0.5,0.3,0.2])

    fcr = (num_contacts == 1 and not reopen and resolution in ['solved','refunded'])
    sla_met = ((first_resp - created).total_seconds()/3600.0) <= sla

    # VOC text and score templates
    if fcr and sla_met and not escalation:
        voc_text = random.choice([
            "Great support, issue resolved quickly and easy to follow.",
            "Very satisfied with the fast resolution.",
            "Agent was helpful and professional.",
            "Excellent service — knowledgeable agent and quick fix.",
            "Super fast response, thank you!",
            "Solved on first contact, much appreciated.",
            "Clear communication and courteous support.",
            "Agent went above and beyond to help.",
            "Problem fixed and explained well.",
            "Smooth process and friendly agent."
        ])
    else:
        voc_text = random.choice([
            "Okay service but took longer than expected.",
            "Support was fine but communication could be clearer.",
            "Issue resolved but needed multiple messages.",
            "Agent helped but I had to repeat details.",
            "Workaround accepted for now; prefer permanent fix.",
            "Average experience — nothing outstanding.",
            "Response was adequate though not fast.",
            "Resolved eventually, but process was clunky.",
            "Support did what was needed, no extras.",
            "Took time but outcome acceptable.",
            "Slow response and still having issues.",
            "Problem persists, not satisfied with the workaround.",
            "Agent was rude and resolution took too long.",
            "Very disappointed — no useful help provided.",
            "Kept getting bounced between agents with no solution.",
            "Unhelpful responses and long delays.",
            "Issue reopened multiple times; very frustrating.",
            "Support ignored important details of my case.",
            "Refund requested but still waiting.",
            "Terrible experience — won't recommend.",
            "This is unacceptable — escalate to a supervisor now.",
            "Agent gave incorrect information and caused more problems.",
            "Repeated outages and no compensation — very unhappy.",
            "I've lost business because of this; expect a claim.",
            "No follow-through from support after multiple promises.",
            "Extremely poor handling — request refund and closure.",
            "Customer service made the issue worse."
        ])
    # scenario tweaks to VOC
    if scenario == "marketing_campaign" and issue in ('billing','account'):
        voc_text += " Confusing billing after the campaign."
    if scenario == "bot_failure":
        voc_text += " Automated help misrouted me."
    if np.random.rand() < 0.1:
        voc_text += " " + fake.sentence(nb_words=6)

    voc_sentiment = sentiment_score(voc_text)  # -1..1
    # map sentiment to 1-5 voc_rating with noise
    voc_base = np.clip(3 + voc_sentiment*1.5 + np.random.normal(0,0.5), 1,5)
    voc_rating = int(round(voc_base))

    # contact cost estimation USD (channel + duration + priority)
    channel_cost_factor = {'phone':1.5,'chat':0.8,'email':0.6,'social':0.7}[channel]
    duration_hours = max(0.01, base_res/8.0)
    contact_cost = round( (2.0 + 10.0*channel_cost_factor) * duration_hours * (1 + 0.2*(priority=='urgent')), 2)
    if scenario == "refund_spike":
        contact_cost *= 1.15
    contact_cost = round(contact_cost, 2)

    weekday_name = created.strftime('%A')
    hour_of_day = created.hour

    tags = []
    if escalation: tags.append('escalated')
    if reopen: tags.append('reopen')
    if issue=='technical' and priority in ('high','urgent'): tags.append('critical')
    cost_to_company_usd = contact_cost
    agent_skill_level = agent_skill

    rows.append({
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "created_at": created,
        "first_response_at": first_resp,
        "closed_at": closed,
        "channel": channel,
        "issue_type": issue,
        "priority": priority,
        "sla_hours": sla,
        "sla_met": sla_met,
        "first_contact_resolution": fcr,
        "num_contacts": int(num_contacts),
        "agent_id": agent_id,
        "customer_tenure_days": customer_tenure_days,
        "customer_segment": customer_segment,
        "voC_rating": voc_rating,
        "voC_text": voc_text,
        "voC_sentiment": voc_sentiment,
        "escalation_flag": escalation,
        "reopen_flag": reopen,
        "resolution_category": resolution,
        "tags": ";".join(tags),
        "cost_to_company_usd": cost_to_company_usd,
        "wait_time_minutes": wait_minutes,
        "product_id": product_id,
        "region": region,
        "timezone": timezone,
        "weekday": weekday_name,
        "hour_of_day": hour_of_day,
        "agent_tenure_days": agent_tenure_days,
        "agent_skill_level": agent_skill_level,
        "contact_cost_usd": contact_cost,
        "scenario": scenario
    })

df = pd.DataFrame(rows)
df['response_time_hours'] = (df['first_response_at'] - df['created_at']).dt.total_seconds()/3600.0
df.to_csv('synthetic_customer_kpi.csv', index=False)
print("Wrote synthetic_customer_kpi.csv, rows:", len(df))

