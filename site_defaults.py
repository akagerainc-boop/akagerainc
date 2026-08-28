"""Default CMS content — used to seed `site_content` and as fallback in the public API."""

WHATSAPP_NUMBER = "250795226123"

BRAND = {
    "name": "Akagera Inc",
    "tagline": "Technology solutions built for what comes next.",
    "primary_color": "#BD4A39",
    "ink": "#141414",
    "paper": "#FFFFFF",
    "logo": "/assets/inc.png",
}

HERO = {
    "kicker": "Akagera Inc — Software Solutions",
    "title": "Technology Solutions Built for What Comes Next.",
    "subtitle": "Akagera Inc builds mobile apps, websites, desktop software, SaaS products, and "
                "custom digital solutions that help individuals, businesses, and organizations "
                "turn ideas into reliable technology.",
    "primary_cta": {"label": "Explore Our Solutions", "url": "/solutions"},
    "secondary_cta": {"label": "Start a Project", "url": "/contact?intent=project"},
}

HOMEPAGE_SECTIONS = [
    {"key": "hero", "label": "Hero", "enabled": True, "order": 1},
    {"key": "product_grid", "label": "Software built by Akagera Inc", "enabled": True, "order": 2},
    {"key": "featured_products", "label": "Featured Akagera Products", "enabled": True, "order": 3},
    {"key": "services", "label": "Services", "enabled": True, "order": 4},
    {"key": "industries", "label": "Industries", "enabled": True, "order": 5},
    {"key": "stats", "label": "Statistics", "enabled": True, "order": 6},
    {"key": "case_studies", "label": "Our Work", "enabled": True, "order": 7},
    {"key": "testimonials", "label": "Testimonials", "enabled": True, "order": 8},
    {"key": "blog", "label": "From the blog", "enabled": True, "order": 9},
    {"key": "cta", "label": "Call to action", "enabled": True, "order": 10},
    {"key": "location", "label": "Our location", "enabled": True, "order": 11},
]

PRODUCT_CATEGORIES = [
    {"name": "Mobile Applications", "slug": "mobile", "icon": "smartphone",
     "description": "Apps built for Android and iOS.", "platforms": ["android", "ios"]},
    {"name": "Web Applications", "slug": "web", "icon": "globe",
     "description": "Modern responsive web platforms.", "platforms": ["web"]},
    {"name": "Windows Software", "slug": "windows", "icon": "monitor",
     "description": "Native, professional Windows applications.", "platforms": ["windows"]},
    {"name": "macOS Software", "slug": "macos", "icon": "command",
     "description": "Software designed for Apple's desktop ecosystem.", "platforms": ["macos"]},
    {"name": "SaaS Platforms", "slug": "saas", "icon": "cloud",
     "description": "Cloud-based software available through subscriptions.", "platforms": ["cloud"]},
    {"name": "Custom Software", "slug": "custom", "icon": "layers",
     "description": "Software designed specifically for organizations and businesses.", "platforms": []},
]

SOCIAL_LINKS = {
    "linkedin": "https://www.linkedin.com/company/akagera-inc",
    "github": "https://github.com/akagerainc-boop",
    "x": "https://x.com/akagerainc",
    "facebook": "https://www.facebook.com/akagerainc",
    "instagram": "https://www.instagram.com/akagerainc",
    "youtube": "https://www.youtube.com/@akagerainc",
}

CONTACT_INFO = {
    "email": "akagerainc@gmail.com",
    "support_email": "support@akagerainc.store",
    "sales_email": "sales@akagerainc.store",
    "phone": "+250 795 226 123",
    "whatsapp": WHATSAPP_NUMBER,
    "address_lines": ["Innovation Hub Building", "Main Street, Musanze District", "Northern Province, Rwanda"],
    "hours": ["Monday - Friday: 8:00 AM - 6:00 PM", "Saturday: 9:00 AM - 1:00 PM", "Sunday: Closed"],
    "map_query": "Musanze,Rwanda",
}

COMPANY_INFO = {
    "who_we_are": "Akagera Inc is a technology and software solutions company. We design, build, and "
                  "maintain software across mobile, web, desktop, and cloud — for individuals, "
                  "businesses, and organizations.",
    "mission": "To create useful, scalable, and reliable technology that helps people and "
               "organizations do more.",
    "vision": "A connected Africa where every organization runs on software it can trust.",
    "values": ["Reliability", "Craft", "Transparency", "Long-term thinking", "Customer obsession"],
    "founded": "2021",
    "headquarters": "Musanze, Rwanda",
}

PRICING = [
    {"name": "Starter", "price": "$49", "currency": "USD", "duration": "30-day service", "popular": False,
     "description": "For a focused piece of work with a clear scope.",
     "features": ["Basic support", "1 project", "30-day delivery window", "Source handover"]},
    {"name": "Professional", "price": "$199", "currency": "USD", "duration": "90-day service", "popular": True,
     "description": "For growing teams that need more surface area and priority help.",
     "features": ["Priority support", "Multiple features", "Priority assistance", "2 revision rounds", "Deployment"]},
    {"name": "Enterprise", "price": "Custom", "currency": "USD", "duration": "Ongoing", "popular": False,
     "description": "For organizations needing dedicated delivery and SLAs.",
     "features": ["Dedicated team", "Advanced security", "SLA", "API integration", "Onboarding & training"]},
]

SEO_DEFAULTS = {
    "title": "Akagera Inc — Software Solutions",
    "description": "Akagera Inc builds software, sells digital products and services, publishes "
                   "applications, and provides licenses, subscriptions, and professional "
                   "technology solutions.",
    "og_image": "/assets/inc.png",
    "site_url": "https://akagerainc.store",
}

INDUSTRIES = [
    {"slug": "education", "name": "Education", "icon": "graduation-cap",
     "summary": "School management, e-learning, and student platforms."},
    {"slug": "finance", "name": "Finance", "icon": "banknote",
     "summary": "Payments, lending, and financial operations software."},
    {"slug": "healthcare", "name": "Healthcare", "icon": "heart-pulse",
     "summary": "Clinic, pharmacy, and patient record systems."},
    {"slug": "retail", "name": "Retail", "icon": "shopping-bag",
     "summary": "POS, inventory, and e-commerce platforms."},
    {"slug": "transportation", "name": "Transportation", "icon": "truck",
     "summary": "Fleet, logistics, and mobility solutions."},
    {"slug": "hospitality", "name": "Hospitality", "icon": "bed",
     "summary": "Hotel, restaurant, and booking systems."},
    {"slug": "government", "name": "Government", "icon": "landmark",
     "summary": "Citizen services and public-sector digital platforms."},
    {"slug": "startups", "name": "Startups", "icon": "rocket",
     "summary": "MVPs and product engineering for founders."},
    {"slug": "small-business", "name": "Small Businesses", "icon": "store",
     "summary": "Affordable websites and business tools."},
    {"slug": "enterprises", "name": "Enterprises", "icon": "building-2",
     "summary": "Custom enterprise software and integrations."},
]

LEGAL_PRIVACY = {"title": "Privacy Policy", "updated": "2026-01-01",
                 "body": "Akagera Inc collects only the information needed to deliver its products "
                         "and services. We never sell your data. Contact "
                         "privacy@akagerainc.store for requests."}
LEGAL_TERMS = {"title": "Terms of Service", "updated": "2026-01-01",
               "body": "By using this website and its services you agree to Akagera Inc's terms. "
                       "Services are delivered according to the scope and duration shown at purchase."}
LEGAL_REFUND = {"title": "Refund Policy", "updated": "2026-01-01",
                "body": "Digital services may be refunded within 14 days if work has not started. "
                        "Licenses and subscriptions are refundable within 14 days if unused."}
LEGAL_COOKIE = {"title": "Cookie Policy", "updated": "2026-01-01",
                "body": "We use essential cookies for authentication and a minimal set of "
                        "analytics cookies. You can decline non-essential cookies."}


DEFAULTS = {
    "brand": BRAND,
    "hero": HERO,
    "homepage_sections": HOMEPAGE_SECTIONS,
    "product_categories": PRODUCT_CATEGORIES,
    "social_links": SOCIAL_LINKS,
    "contact_info": CONTACT_INFO,
    "company_info": COMPANY_INFO,
    "whatsapp": {"number": WHATSAPP_NUMBER, "message": "Hello Akagera Inc, I'd like to talk about a project."},
    "pricing": PRICING,
    "seo_defaults": SEO_DEFAULTS,
    "industries_intro": {"title": "Industry solutions",
                         "subtitle": "Software patterns we've shipped across sectors."},
    "legal_privacy": LEGAL_PRIVACY,
    "legal_terms": LEGAL_TERMS,
    "legal_refund": LEGAL_REFUND,
    "legal_cookie": LEGAL_COOKIE,
}


# ---------------------------------------------------------------------------
#  Default navigation (header mega-menu + footer)
# ---------------------------------------------------------------------------
HEADER_NAV = [
    {"label": "Products", "url": "/products", "children": [
        {"label": "Mobile Apps", "url": "/products?category=mobile"},
        {"label": "Web Applications", "url": "/products?category=web"},
        {"label": "Windows Software", "url": "/products?category=windows"},
        {"label": "macOS Software", "url": "/products?category=macos"},
        {"label": "SaaS Products", "url": "/products?category=saas"},
        {"label": "Enterprise Software", "url": "/products?category=enterprise"},
        {"label": "Developer Tools", "url": "/products?category=developer-tools"},
        {"label": "Digital Products", "url": "/products?category=digital"},
        {"label": "All Products", "url": "/products"},
    ]},
    {"label": "Solutions", "url": "/solutions", "children": [
        {"label": "Business Solutions", "url": "/solutions/business"},
        {"label": "Enterprise Solutions", "url": "/solutions/enterprise"},
        {"label": "Education Solutions", "url": "/solutions/education"},
        {"label": "Startup Solutions", "url": "/solutions/startup"},
        {"label": "E-commerce Solutions", "url": "/solutions/ecommerce"},
        {"label": "Automation Solutions", "url": "/solutions/automation"},
        {"label": "Cloud Solutions", "url": "/solutions/cloud"},
        {"label": "Custom Software", "url": "/solutions/custom-software"},
        {"label": "Digital Transformation", "url": "/solutions/digital-transformation"},
    ]},
    {"label": "Services", "url": "/services", "children": [
        {"label": "Mobile App Development", "url": "/services"},
        {"label": "Web Development", "url": "/services"},
        {"label": "Desktop Application Development", "url": "/services"},
        {"label": "UI/UX Design", "url": "/services"},
        {"label": "Backend Development", "url": "/services"},
        {"label": "API Development", "url": "/services"},
        {"label": "Database Development", "url": "/services"},
        {"label": "Cloud Development", "url": "/services"},
        {"label": "Software Maintenance", "url": "/services"},
        {"label": "App Publishing", "url": "/services"},
        {"label": "Software Consulting", "url": "/services"},
        {"label": "Technical Support", "url": "/services"},
    ]},
    {"label": "Downloads", "url": "/downloads", "children": [
        {"label": "Android APK", "url": "/downloads?platform=android"},
        {"label": "iOS Apps", "url": "/downloads?platform=ios"},
        {"label": "Windows Apps", "url": "/downloads?platform=windows"},
        {"label": "macOS Apps", "url": "/downloads?platform=macos"},
        {"label": "Software Releases", "url": "/downloads"},
        {"label": "Release Notes", "url": "/downloads?view=notes"},
    ]},
    {"label": "Resources", "url": "/documentation", "children": [
        {"label": "Documentation", "url": "/documentation"},
        {"label": "Blog", "url": "/blog"},
        {"label": "Tutorials", "url": "/documentation?section=tutorials"},
        {"label": "Case Studies", "url": "/case-studies"},
        {"label": "FAQs", "url": "/support?view=faq"},
        {"label": "Help Center", "url": "/support"},
        {"label": "Developer Resources", "url": "/documentation?section=developers"},
        {"label": "System Requirements", "url": "/documentation?section=system-requirements"},
    ]},
    {"label": "Company", "url": "/about", "children": [
        {"label": "About Akagera Inc", "url": "/about"},
        {"label": "Careers", "url": "/careers"},
        {"label": "Internships", "url": "/internships"},
        {"label": "Portfolio", "url": "/portfolio"},
        {"label": "Contact", "url": "/contact"},
        {"label": "Business Portal", "url": "/business"},
    ]},
    {"label": "Pricing", "url": "/pricing", "children": []},
]

FOOTER_NAV = [
    {"column_group": "Products", "children": [
        {"label": "Mobile Apps", "url": "/products?category=mobile"},
        {"label": "Web Apps", "url": "/products?category=web"},
        {"label": "Windows Apps", "url": "/products?category=windows"},
        {"label": "macOS Apps", "url": "/products?category=macos"},
        {"label": "SaaS", "url": "/products?category=saas"},
        {"label": "All Products", "url": "/products"},
    ]},
    {"column_group": "Services", "children": [
        {"label": "App Development", "url": "/services"},
        {"label": "Web Development", "url": "/services"},
        {"label": "Desktop Development", "url": "/services"},
        {"label": "UI/UX", "url": "/services"},
        {"label": "Cloud", "url": "/services"},
        {"label": "Consulting", "url": "/services"},
        {"label": "Maintenance", "url": "/services"},
        {"label": "Support", "url": "/support"},
    ]},
    {"column_group": "Company", "children": [
        {"label": "About", "url": "/about"},
        {"label": "Careers", "url": "/careers"},
        {"label": "Internships", "url": "/internships"},
        {"label": "Portfolio", "url": "/portfolio"},
        {"label": "Contact", "url": "/contact"},
    ]},
    {"column_group": "Resources", "children": [
        {"label": "Blog", "url": "/blog"},
        {"label": "Documentation", "url": "/documentation"},
        {"label": "Help Center", "url": "/support"},
        {"label": "FAQs", "url": "/support?view=faq"},
        {"label": "Release Notes", "url": "/downloads?view=notes"},
    ]},
    {"column_group": "Legal", "children": [
        {"label": "Privacy Policy", "url": "/privacy"},
        {"label": "Terms of Service", "url": "/terms"},
        {"label": "Refund Policy", "url": "/refund-policy"},
        {"label": "Cookie Policy", "url": "/cookie-policy"},
    ]},
]
