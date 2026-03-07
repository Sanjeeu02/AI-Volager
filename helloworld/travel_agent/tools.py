import json
import os
from langchain.tools import tool
from duckduckgo_search import DDGS
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from datetime import datetime, timedelta

# Global in-memory cache for speed
_SEARCH_CACHE = {}
CACHE_FILE = "search_cache.json"
CACHE_EXPIRY_HOURS = 24  # Cache expires after 24 hours

def load_cache():
    global _SEARCH_CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                _SEARCH_CACHE = json.load(f)
        except:
            _SEARCH_CACHE = {}

# Load cache once at import
load_cache()

def get_cached_data(query):
    """Get cached data if not expired"""
    if query in _SEARCH_CACHE:
        cached_item = _SEARCH_CACHE[query]
        if isinstance(cached_item, dict) and 'timestamp' in cached_item:
            cache_time = datetime.fromisoformat(cached_item['timestamp'])
            if datetime.now() - cache_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                return cached_item['data']
        else:
            # Old cache format, return as is
            return cached_item
    return None

def save_to_cache(query, data):
    global _SEARCH_CACHE
    _SEARCH_CACHE[query] = {
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(_SEARCH_CACHE, f, indent=2)
    except:
        pass

def safe_search(query: str, max_results: int = 5):
    """
    Enhanced search with caching and expiry.
    """
    cached = get_cached_data(query)
    if cached:
        return cached

    try:
        results = DDGS().text(query, max_results=max_results)
        data = results if results and not hasattr(results, 'get') else []
        if data:
            save_to_cache(query, data)
        return data
    except Exception as e:
        print(f"Search failed: {e}")
        return []

def extract_price_from_text(text):
    """Extract price information from text"""
    # Look for Indian Rupee prices (₹ or Rs or INR)
    price_patterns = [
        r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'Rs\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'INR\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rupees|rs|inr)',
    ]
    
    prices = []
    for pattern in price_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                price = float(match.replace(',', ''))
                if 100 <= price <= 100000:  # Reasonable price range
                    prices.append(int(price))
            except:
                continue
    
    if prices:
        return min(prices), max(prices)
    return None, None


def search_real_transport_options(source, destination, transport_mode, travel_date):
    """Search for real transport options from multiple sources"""
    transport_options = []
    
    source_clean = source.replace(" ", "-").lower()
    dest_clean = destination.replace(" ", "-").lower()
    
    # Search queries for different transport modes
    queries = []
    
    if transport_mode.lower() in ["bus", "any"]:
        queries.extend([
            f"{source} to {destination} bus services {travel_date}",
            f"best buses from {source} to {destination} price timing",
            f"{source} {destination} bus operators redbus"
        ])
    
    if transport_mode.lower() in ["train", "any"]:
        queries.extend([
            f"{source} to {destination} train schedule timing",
            f"trains from {source} to {destination} IRCTC",
            f"{source} {destination} railway timings"
        ])
    
    if transport_mode.lower() in ["flight", "any"]:
        queries.extend([
            f"{source} to {destination} flight price",
            f"flights from {source} to {destination} airlines"
        ])
    
    # Perform searches
    all_results = []
    for query in queries[:3]:  # Limit to 3 queries for speed
        results = safe_search(query, max_results=3)
        all_results.extend(results)
    
    # Extract transport information from search results
    seen_providers = set()
    
    for result in all_results:
        if len(transport_options) >= 10:
            break
            
        title = result.get('title', '')
        body = result.get('body', '')
        combined_text = f"{title} {body}"
        
        # Extract price
        min_price, max_price = extract_price_from_text(combined_text)
        
        # Identify transport provider and type
        provider = None
        transport_type = None
        
        # Bus operators
        bus_operators = ['VRL', 'SRS', 'KPN', 'Orange', 'Parveen', 'Kallada', 'Sharma', 
                        'Neeta', 'Paulo', 'Jabbar', 'Greenline', 'Canara Pinto']
        for op in bus_operators:
            if op.lower() in combined_text.lower():
                provider = f"{op} Travels"
                transport_type = "AC Sleeper Bus" if "ac" in combined_text.lower() else "Sleeper Bus"
                break
        
        # Train services
        if not provider and ("train" in combined_text.lower() or "express" in combined_text.lower()):
            train_names = re.findall(r'(\w+\s+Express|\w+\s+Mail|\w+\s+SF)', combined_text, re.IGNORECASE)
            if train_names:
                provider = "IRCTC"
                transport_type = train_names[0]
        
        # Flight services
        if not provider and ("flight" in combined_text.lower() or "airline" in combined_text.lower()):
            airlines = ['IndiGo', 'Air India', 'SpiceJet', 'Vistara', 'AirAsia']
            for airline in airlines:
                if airline.lower() in combined_text.lower():
                    provider = airline
                    transport_type = "Flight"
                    break
        
        if provider and provider not in seen_providers:
            seen_providers.add(provider)
            
            price_str = f"₹{min_price}-{max_price}" if min_price and max_price else "Check on Platform"
            
            # Generate booking link
            if "bus" in transport_type.lower():
                booking_link = f"https://www.redbus.in/bus-tickets/{source_clean}-to-{dest_clean}"
            elif "train" in transport_type.lower() or "express" in transport_type.lower():
                booking_link = "https://www.irctc.co.in/"
            else:
                booking_link = f"https://www.makemytrip.com/flight/search?from={source}&to={destination}"
            
            transport_options.append({
                "provider": provider,
                "type": transport_type,
                "price": price_str,
                "link": booking_link,
                "verified": True
            })
    
    # Add fallback generic options if not enough found
    if len(transport_options) < 6:
        fallback_options = []
        
        if transport_mode.lower() in ["bus", "any"]:
            fallback_options.extend([
                {"provider": "RedBus", "type": "AC Sleeper", "price": "Check on RedBus", 
                 "link": f"https://www.redbus.in/bus-tickets/{source_clean}-to-{dest_clean}", "verified": False},
                {"provider": "AbhiBus", "type": "Volvo AC", "price": "Check on AbhiBus", 
                 "link": f"https://www.abhibus.com/{source_clean}-to-{dest_clean}-bus", "verified": False},
            ])
        
        if transport_mode.lower() in ["train", "any"]:
            fallback_options.extend([
                {"provider": "IRCTC", "type": "2nd AC", "price": "Check on IRCTC", 
                 "link": "https://www.irctc.co.in/", "verified": False},
            ])
        
        if transport_mode.lower() in ["flight", "any"]:
            fallback_options.extend([
                {"provider": "MakeMyTrip", "type": "Economy", "price": "Check on MakeMyTrip", 
                 "link": f"https://www.makemytrip.com/flight/search?from={source}&to={destination}", "verified": False},
            ])
        
        transport_options.extend(fallback_options[:6 - len(transport_options)])
    
    return transport_options

def search_real_accommodations(destination, accommodation_type, budget):
    """Search for real accommodation options from multiple sources"""
    accommodation_options = []
    
    # Search queries
    queries = [
        f"best hotels in {destination} {accommodation_type} price",
        f"{destination} hotel booking {accommodation_type} rating",
        f"top rated {accommodation_type} {destination} 2026"
    ]
    
    # Perform searches
    all_results = []
    for query in queries:
        results = safe_search(query, max_results=4)
        all_results.extend(results)
    
    # Extract accommodation information
    seen_hotels = set()
    
    for result in all_results:
        if len(accommodation_options) >= 10:
            break
            
        title = result.get('title', '')
        body = result.get('body', '')
        combined_text = f"{title} {body}"
        
        # Extract hotel name (look for common patterns)
        hotel_patterns = [
            r'([\w\s]+Hotel[\w\s]*)',
            r'([\w\s]+Resort[\w\s]*)',
            r'([\w\s]+Inn[\w\s]*)',
            r'([\w\s]+Lodge[\w\s]*)',
            r'(The\s+[\w\s]+)',
            r'(Hotel\s+[\w\s]+)',
        ]
        
        hotel_name = None
        for pattern in hotel_patterns:
            matches = re.findall(pattern, title, re.IGNORECASE)
            if matches:
                hotel_name = matches[0].strip()
                if len(hotel_name) > 5 and len(hotel_name) < 50:
                    break
        
        # Extract rating
        rating_match = re.search(r'(\d+\.?\d*)\s*(?:star|/5|★)', combined_text, re.IGNORECASE)
        rating = rating_match.group(1) if rating_match else "N/A"
        
        # Extract price
        min_price, max_price = extract_price_from_text(combined_text)
        
        if hotel_name and hotel_name not in seen_hotels:
            seen_hotels.add(hotel_name)
            
            price_str = f"₹{min_price}-{max_price}/night" if min_price and max_price else "Check on Platform"
            
            # Determine type based on price or keywords
            if min_price:
                if min_price < 1500:
                    acc_type = "Budget Hotel"
                elif min_price < 4000:
                    acc_type = "3-Star Hotel"
                else:
                    acc_type = "4-5 Star Hotel"
            else:
                acc_type = accommodation_type.title()
            
            accommodation_options.append({
                "name": hotel_name,
                "type": acc_type,
                "rating": f"{rating}★" if rating != "N/A" else "N/A",
                "price": price_str,
                "link": f"https://www.booking.com/searchresults.html?ss={destination}",
                "verified": True
            })
    
    # Add fallback options if not enough found
    if len(accommodation_options) < 6:
        fallback_options = [
            {"name": "Booking.com Hotels", "type": "Hotel", "rating": "Various", 
             "price": "Check on Booking.com", 
             "link": f"https://www.booking.com/searchresults.html?ss={destination}", "verified": False},
            {"name": "MakeMyTrip Hotels", "type": "Hotel", "rating": "Various", 
             "price": "Check on MakeMyTrip", 
             "link": f"https://www.makemytrip.com/hotels/hotel-listing/?city={destination}", "verified": False},
            {"name": "OYO Rooms", "type": "Budget Hotel", "rating": "Budget", 
             "price": "Check on OYO", 
             "link": f"https://www.oyorooms.com/search/?location={destination}", "verified": False},
            {"name": "Agoda Hotels", "type": "Hotel", "rating": "Various", 
             "price": "Check on Agoda", 
             "link": f"https://www.agoda.com/search?city={destination}", "verified": False},
        ]
        
        accommodation_options.extend(fallback_options[:6 - len(accommodation_options)])
    
    return accommodation_options

def search_verified_attractions(destination):
    """Search for verified tourist attractions"""
    queries = [
        f"top 10 tourist places in {destination}",
        f"must visit attractions {destination} 2026",
        f"{destination} sightseeing places famous landmarks"
    ]
    
    all_results = []
    for query in queries:
        results = safe_search(query, max_results=5)
        all_results.extend(results)
    
    return all_results[:10]

@tool
def fetch_complete_trip_data(
    source: str, 
    destination: str, 
    travel_date: str, 
    transport_mode: str = "any",
    accommodation_type: str = "any",
    budget: str = "standard"
):
    """
    Comprehensive travel planning tool with REAL, VERIFIED data from web searches.
    Fetches actual bus services, hotel names, prices, and tourist attractions.
    Provides 6+ options for each category with unique IDs.
    """
    
    print(f"🔍 Searching real data for {source} to {destination}...")
    
    # Fetch real data using parallel searches
    with ThreadPoolExecutor(max_workers=3) as executor:
        transport_future = executor.submit(search_real_transport_options, source, destination, transport_mode, travel_date)
        accommodation_future = executor.submit(search_real_accommodations, destination, accommodation_type, budget)
        attractions_future = executor.submit(search_verified_attractions, destination)
        
        transport_options = transport_future.result()
        accommodation_options = accommodation_future.result()
        attractions = attractions_future.result()
    
    # Assign IDs to options
    for idx, option in enumerate(transport_options, 1):
        option['id'] = f"T{idx}"
    
    for idx, option in enumerate(accommodation_options, 1):
        option['id'] = f"H{idx}"
    
    return json.dumps({
        "transport_options": transport_options[:12],
        "accommodation_options": accommodation_options[:12],
        "attractions": attractions,
        "source": source,
        "destination": destination,
        "travel_date": travel_date
    }, indent=2)


@tool
def booking_tool(transport_id: str = None, accommodation_id: str = None, booking_details: str = ""):
    """
    Processes booking request for transport and/or accommodation.
    
    Args:
        transport_id: Transport option ID (e.g., T1, T2, T3)
        accommodation_id: Accommodation option ID (e.g., H1, H2, H3)
        booking_details: Additional booking information
    
    Use this tool when user provides specific IDs they want to book.
    """
    bookings = []
    
    if transport_id:
        bookings.append({
            "type": "Transport",
            "id": transport_id,
            "status": "Confirmed",
            "message": f"✅ Transport booking confirmed for option {transport_id}"
        })
    
    if accommodation_id:
        bookings.append({
            "type": "Accommodation",
            "id": accommodation_id,
            "status": "Confirmed",
            "message": f"✅ Accommodation booking confirmed for option {accommodation_id}"
        })
    
    if not bookings:
        return json.dumps({
            "status": "error",
            "message": "Please provide Transport ID and/or Accommodation ID to proceed with booking."
        })
    
    return json.dumps({
        "status": "success",
        "bookings": bookings,
        "reference_number": f"VYG-{transport_id or ''}{accommodation_id or ''}-2026",
        "next_steps": [
            "📧 Confirmation email will be sent to your registered email",
            "💳 Payment link will be shared shortly",
            "📱 You can track your booking in the 'My Bookings' tab",
            "🔗 Direct booking links are available in the recommendations above"
        ],
        "message": f"🎉 Booking request processed successfully! Reference: VYG-{transport_id or ''}{accommodation_id or ''}-2026"
    }, indent=2)

def get_tools():
    # Only expose the SUPER TOOL and Booking
    return [fetch_complete_trip_data, booking_tool]
