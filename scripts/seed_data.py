import requests
import random
import time
from datetime import datetime, timedelta

BASE = "http://localhost:8888/index.php/api/v1"
AUTH = ("admin", "admin123")

# Create services
services_data = [
    {"name": "Men's Haircut", "duration": 30, "price": 35, "currency": "USD", "attendantsNumber": 1},
    {"name": "Women's Haircut", "duration": 45, "price": 55, "currency": "USD", "attendantsNumber": 1},
    {"name": "Kids Haircut", "duration": 20, "price": 20, "currency": "USD", "attendantsNumber": 1},
    {"name": "Full Color", "duration": 90, "price": 120, "currency": "USD", "attendantsNumber": 1},
    {"name": "Highlights", "duration": 120, "price": 150, "currency": "USD", "attendantsNumber": 1},
    {"name": "Balayage", "duration": 150, "price": 200, "currency": "USD", "attendantsNumber": 1},
    {"name": "Deep Conditioning", "duration": 30, "price": 40, "currency": "USD", "attendantsNumber": 1},
    {"name": "Keratin Treatment", "duration": 120, "price": 250, "currency": "USD", "attendantsNumber": 1},
    {"name": "Manicure", "duration": 30, "price": 30, "currency": "USD", "attendantsNumber": 1},
    {"name": "Gel Manicure", "duration": 45, "price": 45, "currency": "USD", "attendantsNumber": 1},
    {"name": "Blowout", "duration": 30, "price": 40, "currency": "USD", "attendantsNumber": 1},
    {"name": "Beard Trim", "duration": 15, "price": 15, "currency": "USD", "attendantsNumber": 1},
]

services = []
for svc in services_data:
    r = requests.post(f"{BASE}/services", auth=AUTH, json=svc)
    if r.status_code == 201:
        services.append(r.json())
        print(f"Service: {svc['name']} -> ID {r.json()['id']}")

service_ids = [s["id"] for s in services]

# Create providers (staff)
working_plan = {
    "monday": {"start": "09:00", "end": "18:00", "breaks": [{"start": "12:00", "end": "13:00"}]},
    "tuesday": {"start": "09:00", "end": "18:00", "breaks": [{"start": "12:00", "end": "13:00"}]},
    "wednesday": {"start": "09:00", "end": "18:00", "breaks": [{"start": "12:00", "end": "13:00"}]},
    "thursday": {"start": "09:00", "end": "18:00", "breaks": [{"start": "12:00", "end": "13:00"}]},
    "friday": {"start": "09:00", "end": "17:00", "breaks": [{"start": "12:00", "end": "13:00"}]},
    "saturday": {"start": "10:00", "end": "15:00", "breaks": []},
    "sunday": None,
}

providers_data = [
    {"firstName": "Sarah", "lastName": "Johnson", "email": "sarah@testsalon.com", "phone": "+1-555-0101"},
    {"firstName": "Mike", "lastName": "Chen", "email": "mike@testsalon.com", "phone": "+1-555-0102"},
    {"firstName": "Emma", "lastName": "Williams", "email": "emma@testsalon.com", "phone": "+1-555-0103"},
    {"firstName": "Carlos", "lastName": "Rivera", "email": "carlos@testsalon.com", "phone": "+1-555-0104"},
    {"firstName": "Lisa", "lastName": "Park", "email": "lisa@testsalon.com", "phone": "+1-555-0105"},
]

providers = []
for prov in providers_data:
    prov.update({
        "timezone": "America/New_York",
        "language": "english",
        "services": service_ids,
        "settings": {
            "username": prov["firstName"].lower() + prov["lastName"].lower(),
            "password": "test1234",
            "notifications": True,
            "calendarView": "default",
            "workingPlan": working_plan,
        },
    })
    r = requests.post(f"{BASE}/providers", auth=AUTH, json=prov)
    if r.status_code == 201:
        providers.append(r.json())
        print(f"Provider: {prov['firstName']} {prov['lastName']} -> ID {r.json()['id']}")

# Create customers
customers_data = [
    {"firstName": "Alice", "lastName": "Brown", "email": "alice@email.com", "phone": "+1-555-1001"},
    {"firstName": "Bob", "lastName": "Smith", "email": "bob@email.com", "phone": "+1-555-1002"},
    {"firstName": "Carol", "lastName": "Davis", "email": "carol@email.com", "phone": "+1-555-1003"},
    {"firstName": "David", "lastName": "Wilson", "email": "david@email.com", "phone": "+1-555-1004"},
    {"firstName": "Eve", "lastName": "Martinez", "email": "eve@email.com", "phone": "+1-555-1005"},
    {"firstName": "Frank", "lastName": "Taylor", "email": "frank@email.com", "phone": "+1-555-1006"},
    {"firstName": "Grace", "lastName": "Anderson", "email": "grace@email.com", "phone": "+1-555-1007"},
    {"firstName": "Henry", "lastName": "Thomas", "email": "henry@email.com", "phone": "+1-555-1008"},
    {"firstName": "Ivy", "lastName": "Jackson", "email": "ivy@email.com", "phone": "+1-555-1009"},
    {"firstName": "Jack", "lastName": "White", "email": "jack@email.com", "phone": "+1-555-1010"},
    {"firstName": "Karen", "lastName": "Harris", "email": "karen@email.com", "phone": "+1-555-1011"},
    {"firstName": "Leo", "lastName": "Clark", "email": "leo@email.com", "phone": "+1-555-1012"},
    {"firstName": "Mia", "lastName": "Lewis", "email": "mia@email.com", "phone": "+1-555-1013"},
    {"firstName": "Noah", "lastName": "Walker", "email": "noah@email.com", "phone": "+1-555-1014"},
    {"firstName": "Olivia", "lastName": "Hall", "email": "olivia@email.com", "phone": "+1-555-1015"},
]

customers = []
for cust in customers_data:
    cust.update({"timezone": "America/New_York", "language": "english"})
    r = requests.post(f"{BASE}/customers", auth=AUTH, json=cust)
    if r.status_code == 201:
        customers.append(r.json())
        print(f"Customer: {cust['firstName']} {cust['lastName']} -> ID {r.json()['id']}")

provider_ids = [p["id"] for p in providers]
customer_ids = [c["id"] for c in customers]

# Create appointments over 60 days
created = 0
start_date = datetime(2026, 1, 5)
for day_offset in range(60):
    date = start_date + timedelta(days=day_offset)
    if date.weekday() == 6:
        continue
    for provider_id in provider_ids:
        slots = random.sample([9, 10, 11, 13, 14, 15, 16], k=random.randint(2, 4))
        for hour in slots:
            svc = random.choice(services)
            start = date.replace(hour=hour, minute=0)
            end = start + timedelta(minutes=min(svc["duration"], 55))
            appt = {
                "start": start.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end.strftime("%Y-%m-%d %H:%M:%S"),
                "location": "Test Salon - Main Branch",
                "customerId": random.choice(customer_ids),
                "providerId": provider_id,
                "serviceId": svc["id"],
            }
            r = requests.post(f"{BASE}/appointments", auth=AUTH, json=appt)
            if r.status_code == 201:
                created += 1
            elif r.status_code == 429:
                time.sleep(30)
                r = requests.post(f"{BASE}/appointments", auth=AUTH, json=appt)
                if r.status_code == 201:
                    created += 1

print(f"\n--- Seed Complete ---")
print(f"Services: {len(services)}")
print(f"Providers: {len(providers)}")
print(f"Customers: {len(customers)}")
print(f"Appointments: {created}")