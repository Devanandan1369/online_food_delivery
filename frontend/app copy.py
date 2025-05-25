import streamlit as st
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO

MENU_SERVICE_URL = "http://127.0.0.1:5001"
ORDER_SERVICE_URL = "http://127.0.0.1:5002"

st.set_page_config(page_title="🍔 Online Food Delivery App", layout="wide", initial_sidebar_state="expanded")
st.title("🍔 Online Food Delivery App")

# ----- Utils -----
def format_currency(value):
  return f"${value:.2f}"

@st.cache_data(ttl=600)
def get_restaurants():
    try:
        res = requests.get(f"{MENU_SERVICE_URL}/menus")
        res.raise_for_status()
        return res.json()
    except Exception:
        return []

# Added cache-buster param here:
@st.cache_data(ttl=600)
def get_orders(cache_buster=0):
    try:
        res = requests.get(f"{ORDER_SERVICE_URL}/orders")
        res.raise_for_status()
        return res.json()
    except Exception:
        return []

def load_image_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception:
        return None

# ----- Load restaurants -----
restaurants = get_restaurants()
if not restaurants:
    st.error("Failed to load restaurants. Please check if menu service is running.")
    st.stop()

# Initialize session state for cart and order refresh counter
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'orders_refresh' not in st.session_state:
    st.session_state.orders_refresh = 0

# Sidebar - select restaurant
st.sidebar.header("Select Restaurant")
restaurant_names = [r['name'] for r in restaurants]
selected_restaurant_name = st.sidebar.selectbox("Choose a restaurant", restaurant_names)
selected_restaurant = next(r for r in restaurants if r['name'] == selected_restaurant_name)
menu_items = selected_restaurant.get('items', [])

# Sidebar - Search & Filters
st.sidebar.markdown("---")
st.sidebar.header("Filter Menu Items")

search_query = st.sidebar.text_input("Search by name...")
min_price = st.sidebar.number_input("Min price", min_value=0.0, value=0.0, step=0.5)
max_price = st.sidebar.number_input("Max price", min_value=0.0, value=100.0, step=0.5)

def filter_menu(items, search, min_p, max_p):
    filtered = []
    for item in items:
        name = item.get('name', '').lower()
        price = item.get('price', 0)
        if search.lower() in name and min_p <= price <= max_p:
            filtered.append(item)
    return filtered

filtered_menu = filter_menu(menu_items, search_query, min_price, max_price)

# ----- Cart management -----
def add_to_cart(item_id, item_name, price, qty):
    if qty <= 0:
        return
    if item_id in st.session_state.cart:
        st.session_state.cart[item_id]['quantity'] += qty
    else:
        st.session_state.cart[item_id] = {'name': item_name, 'price': price, 'quantity': qty}

def remove_from_cart(item_id):
    if item_id in st.session_state.cart:
        del st.session_state.cart[item_id]

def update_cart_quantity(item_id, qty):
    if qty <= 0:
        remove_from_cart(item_id)
    else:
        st.session_state.cart[item_id]['quantity'] = qty

# ----- Main layout -----
col1, col2 = st.columns([3, 1])

with col1:
    st.header(f"Menu for {selected_restaurant_name}")

    if not filtered_menu:
        st.info("No menu items match your search/filter criteria.")
    else:
        for item in filtered_menu:
            item_id = item['id']
            with st.container():
                cols = st.columns([1, 4, 1, 1])
                img = None
                if 'image_url' in item:
                    img = load_image_from_url(item['image_url'])
                if img:
                    cols[0].image(img, width=64)
                else:
                    cols[0].write("🍽️")

                cols[1].markdown(f"**{item['name']}**  \n{item.get('description', '')}")
                cols[1].markdown(f"Price: {format_currency(item['price'])}")
                qty = cols[2].number_input("Qty", min_value=0, max_value=20, key=f"qty_{item_id}", value=0, label_visibility="collapsed")
                add_clicked = cols[3].button("Add", key=f"add_{item_id}")
                if add_clicked and qty > 0:
                    add_to_cart(item_id, item['name'], item['price'], qty)
                    st.toast(f"Added {qty} x {item['name']} to cart", icon="✅")

with col2:
    st.header("🛒 Cart Summary")
    if not st.session_state.cart:
        st.info("Your cart is empty.")
    else:
        total_price = 0
        for item_id, details in st.session_state.cart.items():
            st.write(f"**{details['name']}**")
            qty = st.number_input("Qty", min_value=0, max_value=50, value=details['quantity'], key=f"cart_qty_{item_id}")
            if qty != details['quantity']:
                update_cart_quantity(item_id, qty)
                st.rerun()
            price = details['price']
            subtotal = price * qty
            total_price += subtotal
            st.write(f"Price: {format_currency(price)}  |  Subtotal: {format_currency(subtotal)}")
            remove = st.button("Remove", key=f"remove_{item_id}")
            if remove:
                remove_from_cart(item_id)
                st.rerun()
            st.markdown("---")

        st.markdown(f"### Total: {format_currency(total_price)}")

        # Place order form
        st.header("Place Your Order")
        customer_name = st.text_input("Your Name", max_chars=50)
        address = st.text_area("Delivery Address", max_chars=200)
        place_order = st.button("Confirm Order")

        if place_order:
            if not customer_name.strip() or not address.strip():
                st.error("Please provide both your name and delivery address.")
            elif not st.session_state.cart:
                st.error("Your cart is empty.")
            else:
                order_items = []
                for details in st.session_state.cart.values():
                    order_items.append({
                        "name": details['name'],
                        "price": details['price'],
                        "quantity": details['quantity']
                    })
                order_data = {
                    "customer_name": customer_name.strip(),
                    "address": address.strip(),
                    "restaurant": selected_restaurant_name,
                    "items": order_items,
                    "total": total_price,
                    "timestamp": datetime.now().isoformat()  # ✅ Add timestamp here
                }
                try:
                    resp = requests.post(f"{ORDER_SERVICE_URL}/order", json=order_data)
                    if resp.status_code == 201:
                        st.success("🎉 Order placed successfully!")
                        st.session_state.cart.clear()
                        st.session_state.orders_refresh += 1  # Bust cache here
                        st.rerun()
                    else:
                        st.error(f"Failed to place order: {resp.text}")
                except Exception as e:
                    st.error(f"Error placing order: {e}")

# --- Past orders ---
st.markdown("---")
st.header("📦 Past Orders")

orders = get_orders(st.session_state.orders_refresh)  # pass cache_buster here
if not orders:
    st.info("No past orders found.")
else:
    def sort_key(o):
        ts = o.get("timestamp")
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.min

    orders_sorted = sorted(orders, key=sort_key, reverse=True)

    for order in orders_sorted:
        order_id = order.get('order_id', 'N/A')
        restaurant = order.get('restaurant', 'Unknown Restaurant')
        customer = order.get('customer_name', 'Unknown')
        addr = order.get('address', 'Unknown')
        ts = order.get('timestamp')
        try:
            ts_fmt = datetime.fromisoformat(ts).strftime("%b %d, %Y, %I:%M %p") if ts else "Unknown"
        except Exception:
            ts_fmt = ts or "Unknown"
        total = order.get('total', 0)
        items = order.get('items', [])

        with st.expander(f"Order #{order_id} — {restaurant} ({ts_fmt})"):
            st.markdown(f"**Customer:** {customer}")
            st.markdown(f"**Address:** {addr}")
            st.markdown("**Items:**")
            for item in items:
                name = item.get('name', 'Unknown')
                qty = item.get('quantity', '?')
                price = item.get('price', 0)
                st.write(f"- {name} x {qty} @ {format_currency(price)} each")
            st.markdown(f"### Total Paid: {format_currency(total)}")
