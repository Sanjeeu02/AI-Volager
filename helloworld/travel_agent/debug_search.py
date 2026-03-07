from duckduckgo_search import DDGS

print("Testing DuckDuckGo Search...")
try:
    results = DDGS().text("flights from New York to London", max_results=3)
    if results:
        print("Success! Found results:")
        for r in results:
            print(f"- {r.get('title')}: {r.get('href')}")
    else:
        print("Search returned empty list.")
except Exception as e:
    print(f"Search FAILED with error: {e}")
