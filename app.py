from flask import Flask, render_template, request, redirect, url_for
import random
from datetime import datetime, timedelta
from collections import deque
import math

app = Flask(__name__)

# -------------------------
# Queue: Orders waiting to be assigned
order_queue = deque()

# Reference point for coordinates
REFERENCE_POINT = (0, 0)

# Delivery agents
delivery_agents = [
    {"id": 1, "name": "Agent A", "location": (5, 5), "available": True, "order_id": None},
    {"id": 2, "name": "Agent B", "location": (10, 2), "available": True, "order_id": None},
    {"id": 3, "name": "Agent C", "location": (3, 8), "available": True, "order_id": None},
]

# Orders list
orders = []

# Stack for rollback
rollback_stack = []

# Hash map for agent status
agent_status = {agent["id"]: agent for agent in delivery_agents}

# Menu items
menu_items = [
    {"name": "Pizza", "price": 250},
    {"name": "Burger", "price": 150},
    {"name": "Pasta", "price": 200},
    {"name": "Sandwich", "price": 100}
]

# -------------------------
def calculate_distance_km(loc1, loc2):
    return math.sqrt((loc1[0]-loc2[0])**2 + (loc1[1]-loc2[1])**2)

# Assign nearest available agent
def assign_agent(order):
    available_agents = [a for a in delivery_agents if a["available"]]
    if not available_agents:
        order_queue.append(order)
        return None
    nearest_agent = min(available_agents, key=lambda a: calculate_distance_km(a["location"], order["location"]))
    nearest_agent["available"] = False
    nearest_agent["order_id"] = order["id"]
    agent_status[nearest_agent["id"]] = nearest_agent
    order["agent_id"] = nearest_agent["id"]
    order["status"] = "Assigned"
    distance = calculate_distance_km(nearest_agent["location"], order["location"])
    eta_minutes = int(distance) + random.randint(5, 15)
    order["eta"] = datetime.now() + timedelta(minutes=eta_minutes)
    return nearest_agent

# -------------------------
@app.route('/')
def index():
    return render_template('index.html', orders=orders, agents=delivery_agents, queue=list(order_queue), menu_items=menu_items)

@app.route('/add_order', methods=['POST'])
def add_order():
    customer_name = request.form['customer_name']
    location_x = float(request.form['location_x'])
    location_y = float(request.form['location_y'])

    # Collect selected menu items and quantities
    selected_items = []
    for item in menu_items:
        qty = request.form.get(f"qty_{item['name']}")
        if qty and qty.isdigit() and int(qty) > 0:
            selected_items.append({"name": item["name"], "quantity": int(qty), "price": item["price"]})

    order_id = len(orders) + 1
    order = {
        "id": order_id,
        "customer_name": customer_name,
        "location": (location_x, location_y),
        "status": "Pending",
        "agent_id": None,
        "eta": None,
        "items": selected_items
    }
    orders.append(order)
    assign_agent(order)
    return redirect(url_for('index'))

@app.route('/cancel_order/<int:order_id>')
def cancel_order(order_id):
    order = next((o for o in orders if o["id"] == order_id), None)
    if order and order["status"] != "Delivered":
        order["status"] = "Cancelled"
        if order["agent_id"]:
            agent = agent_status[order["agent_id"]]
            agent["available"] = True
            agent["order_id"] = None
            if order_queue:
                next_order = order_queue.popleft()
                assign_agent(next_order)
    return redirect(url_for('index'))

@app.route('/reassign_order/<int:order_id>')
def reassign_order(order_id):
    order = next((o for o in orders if o["id"] == order_id), None)
    if order and order["status"] != "Delivered":
        if order["agent_id"]:
            old_agent = agent_status[order["agent_id"]]
            old_agent["available"] = True
            old_agent["order_id"] = None
        assign_agent(order)
    return redirect(url_for('index'))

@app.route('/rollback')
def rollback():
    if rollback_stack:
        order, agent = rollback_stack.pop()
        order["status"] = "Pending"
        agent["available"] = True
        agent["order_id"] = None
    return redirect(url_for('index'))

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT or default 5000
    app.run(host="0.0.0.0", port=port, debug=True)


