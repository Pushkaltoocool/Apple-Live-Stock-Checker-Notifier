from playwright.sync_api import sync_playwright, TimeoutError
import time, json
from notify import notify_both

URL = "https://www.apple.com/sg/shop/buy-iphone/iphone-17-pro/6.9-inch-display-512gb-silver"
POSTAL_CODE = "819666"

def text_or_none(locator):
    try:
        return locator.inner_text().strip()
    except Exception:
        return None

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,   # must be visible for Apple’s anti-bot DOM to render fully
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
        )
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 900},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/141.0.0.0 Safari/537.36")
        )
        page = ctx.new_page()

        print("🌐 Navigating to Apple Store…")
        page.goto(URL, timeout=60000)
        page.wait_for_load_state("networkidle")

        # ---- 1. Select No AppleCare ----
        page.wait_for_selector("input[name='applecare-options'][data-autom='noapplecare']", timeout=20000)
        page.locator("input[name='applecare-options'][data-autom='noapplecare']").click()
        print("✅ Selected 'No AppleCare'")

        # ---- 2. Click 'Check availability' ----
        for _ in range(12):
            if page.locator("button[data-autom='productLocatorTriggerLink']").count() > 0:
                break
            page.mouse.wheel(0, 600)
            time.sleep(0.25)
        btn = page.locator("button[data-autom='productLocatorTriggerLink']")
        if btn.count() == 0:
            raise RuntimeError("❌ Could not find 'Check availability' button.")
        btn.scroll_into_view_if_needed()
        btn.click()
        print("✅ Opened pickup overlay")

        # ---- 3. Enter postal code ----
        page.wait_for_selector("input[data-autom='zipCode']", timeout=20000)
        postal = page.locator("input[data-autom='zipCode']")
        postal.fill(POSTAL_CODE)
        postal.press("Enter")
        print(f"📮 Searched postal code {POSTAL_CODE}")

        # ---- 4. Wait for results ----
        page.wait_for_selector("div.rf-productlocator-options", timeout=20000)
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)

        # Reveal “Similar models” section
        page.mouse.wheel(0, 3000)
        time.sleep(1.5)
        page.evaluate("""
          document.querySelectorAll('.rf-productlocator-suggestionoptions[aria-hidden="true"]').forEach(e => e.setAttribute('aria-hidden','false'));
          document.querySelectorAll('.rf-productlocator-suggestionitem').forEach(e => e.style.display='block');
        """)

        # ---- 5. Parse data ----
        data = {
            "product": {},
            "pickup": {"postal_code": POSTAL_CODE, "header": None, "summary": None, "stores": []},
            "delivery": None,
            "similar_models": []
        }

        # Product
        prod_info = page.locator("div.rf-productlocator-productinfo")
        data["product"]["title"] = text_or_none(prod_info.locator(".typography-body-tight"))
        data["product"]["price"] = text_or_none(prod_info.locator(".rf-productlocator-productprice"))
        data["product"]["image_alt"] = text_or_none(page.locator(".rf-productlocator-productimg img").first)

        # Pickup header + summary
        data["pickup"]["header"] = text_or_none(page.locator(".rf-productlocator-pickuploctionheader h3"))
        summary_btn = page.locator(".rf-productlocator-pickupstoreslist .rf-productlocator-buttontitle")
        data["pickup"]["summary"] = text_or_none(summary_btn)

        # Stores list
        for item in page.locator("li.rf-productlocator-storeoption").all():
            left, right = item.locator(".form-selector-left-col"), item.locator(".form-selector-right-col")
            labels = left.locator(".form-label-small")
            data["pickup"]["stores"].append({
                "store": text_or_none(left.locator(".form-selector-title")),
                "city": text_or_none(labels.nth(0)) if labels.count() > 0 else None,
                "distance": text_or_none(labels.nth(1)) if labels.count() > 1 else None,
                "status": text_or_none(right.locator("span").nth(0)),
                "pickup_type": text_or_none(right.locator(".form-label-small").nth(0))
            })

        # Delivery
        data["delivery"] = text_or_none(page.locator(".rf-productlocator-deliveryquotes .form-selector-title"))

        # Similar models
        try:
            page.wait_for_selector(".rf-productlocator-suggestionitem", timeout=7000)
        except TimeoutError:
            print("⚠️ No 'Similar models' section visible.")
        else:
            for card in page.locator(".rf-productlocator-suggestionitem").all():
                toggle = card.locator(".rf-productlocator-suggestionstogglebtn")
                header_texts = toggle.locator(".rf-productlocator-togglebtn-content").locator("*")
                model_name = price = availability_label = None
                for t in header_texts.all_inner_texts():
                    t = t.strip()
                    if not t:
                        continue
                    if "S$" in t:
                        price = t
                    elif "Available" in t or "store" in t.lower():
                        availability_label = t
                    else:
                        model_name = t if model_name is None else model_name
                try:
                    if toggle.get_attribute("aria-expanded") != "true":
                        toggle.click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(0.5)
                except Exception:
                    pass
                sim_stores = []
                for s in card.locator("li.rf-productlocator-storeoption").all():
                    left, right = s.locator(".form-selector-left-col"), s.locator(".form-selector-right-col")
                    labs = left.locator(".form-label-small")
                    sim_stores.append({
                        "store": text_or_none(left.locator(".form-selector-title")),
                        "city": text_or_none(labs.nth(0)) if labs.count() > 0 else None,
                        "distance": text_or_none(labs.nth(1)) if labs.count() > 1 else None,
                        "status": text_or_none(right.locator("span").nth(0)),
                        "pickup_type": text_or_none(right.locator(".form-label-small").nth(0))
                    })
                data["similar_models"].append({
                    "model": model_name, "price": price,
                    "availability_summary": availability_label, "stores": sim_stores
                })

        # ---- 6. Output + notify ----
        print("\n=== JSON OUTPUT ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        print("\n=== SUMMARY ===")
        print(f"{data['product'].get('title','?')} — {data['product'].get('price','?')}")
        print(data['pickup'].get('header') or "")
        print(data['pickup'].get('summary') or "")
        for s in data["pickup"]["stores"]:
            print(f"🏬 {s['store']} — {s['city']} — {s['distance']} | {s['status']} ({s['pickup_type']})")
        if data["delivery"]:
            print(f"\n🚚 {data['delivery']}")
        if data["similar_models"]:
            print("\n🧩 Similar models available:")
            for sm in data["similar_models"]:
                print(f"• {sm['model']} — {sm['price']} — {sm['availability_summary']}")
                for st in sm["stores"]:
                    print(f"   └ {st['store']} — {st['status']}")

        # Send to Telegram + Discord
        notify_both(data)

        browser.close()

if __name__ == "__main__":
    run()

