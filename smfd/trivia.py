"""Stock + market trivia, freshly drawn every visit.

The view hands in a per-session ``random.Random`` (seeded once per browser
session), so facts stay put while a visitor clicks around but reshuffle on
their next visit. Facts are curated true-or-carefully-hedged one-liners —
add freely, but keep them verifiable.
"""

from __future__ import annotations

import random

STOCK_TRIVIA = {
    "AAPL": [
        "Apple's first logo featured Isaac Newton sitting under a tree.",
        "The original Apple I computer sold for $666.66.",
        "Apple was the first U.S. company to reach a $1 trillion market value (2018) — and the first to $3 trillion (2022).",
    ],
    "MSFT": [
        "Microsoft's first product was a BASIC interpreter for the Altair 8800.",
        "Bill Gates' SAT score was 1590 out of 1600.",
        "The name 'Microsoft' is a blend of 'microcomputer' and 'software'.",
    ],
    "AMZN": [
        "Amazon was originally going to be called 'Cadabra' (as in abracadabra).",
        "Jeff Bezos' first office desk was made from a door.",
        "Amazon's first book order was 'Fluid Concepts and Creative Analogies'.",
    ],
    "GOOG": [
        "Google's original name was 'BackRub'.",
        "The first Google Doodle was a Burning Man stick figure in 1998.",
        "'Googol' (the number 10^100) inspired the name Google.",
    ],
    "META": [
        "Facebook was originally limited to Harvard students only.",
        "The iconic blue color was chosen because Zuckerberg is red-green colorblind.",
        "Facebook's 'Like' button was almost called the 'Awesome' button.",
    ],
    "NVDA": [
        "NVIDIA's name comes from 'invidia', the Latin word for envy.",
        "The company was founded in a Denny's restaurant in 1993.",
        "NVIDIA's first product, the NV1, could also play Sega Saturn games.",
        "NVIDIA went from a $1 trillion to a $3 trillion market value in about a year (2023–24).",
    ],
    "NFLX": [
        "Netflix was founded because Reed Hastings got a $40 late fee from Blockbuster.",
        "Netflix's first DVD shipped was 'Beetlejuice' in 1998.",
        "The company considered naming itself 'Kibble' at one point.",
    ],
    "DIS": [
        "Walt Disney was fired from a newspaper for 'lacking imagination'.",
        "Mickey Mouse was originally going to be named 'Mortimer Mouse'.",
        "Disney World is roughly the same size as San Francisco.",
    ],
    "COST": [
        "Costco sells more hot dogs than every MLB stadium combined.",
        "The Costco hot dog combo has been $1.50 since 1985.",
        "Costco's Kirkland Signature is one of the largest brands in the world.",
    ],
    "COIN": [
        "Coinbase was the first crypto company to go public on the Nasdaq.",
        "The company was founded in a two-bedroom apartment in San Francisco.",
    ],
    "AMD": [
        "AMD was founded by Jerry Sanders, a former Fairchild Semiconductor exec.",
        "AMD and Intel were both founded within a year of each other (1968-1969).",
        "Lisa Su took over as CEO in 2014 when AMD traded under $4 — one of tech's great turnarounds.",
    ],
    "INTC": [
        "Intel's first product was a memory chip, not a processor.",
        "The Intel Inside jingle is one of the most recognized sounds in advertising.",
        "Gordon Moore (of Moore's Law) co-founded Intel.",
    ],
    "WMT": [
        "The first Walmart opened in 1962 in Rogers, Arkansas.",
        "Walmart is the world's largest employer with over 2 million workers.",
    ],
    "BRK-B": [
        "Berkshire Hathaway was originally a textile company.",
        "Warren Buffett bought his first stock at age 11.",
        "Berkshire's Class A shares have never split and are the most expensive stock in the world.",
    ],
    "RBLX": [
        "Over half of American kids under 16 play Roblox.",
        "Roblox was originally called 'DynaBlocks' when it launched in 2004.",
    ],
    "MCD": [
        "McDonald's serves about 69 million customers daily worldwide.",
        "The Big Mac was invented by a franchisee, not McDonald's corporate.",
    ],
    "PLTR": [
        "Palantir is named after the seeing stones in Lord of the Rings.",
        "The company was co-founded by Peter Thiel and Alex Karp.",
    ],
    "MSTR": [
        "MicroStrategy holds over 200,000 Bitcoin on its balance sheet.",
        "The company rebranded to 'Strategy' but its ticker is still MSTR.",
    ],
    "SNDK": [
        "SanDisk was founded in 1988 as 'SunDisk' — renamed in 1995 to avoid confusion with Sun Microsystems.",
        "SanDisk's founders helped pioneer the flash memory card formats used in cameras and phones.",
        "SanDisk returned to the stock market in 2025 after being spun back out of Western Digital.",
    ],
    "ARM": [
        "Arm began in 1990 as a 12-person joint venture working out of a converted turkey barn in Cambridge, England.",
        "ARM originally stood for 'Acorn RISC Machine' — Apple was a founding investor, needing a chip for the Newton.",
        "Arm designs are inside roughly 99% of the world's smartphones — yet Arm manufactures nothing itself.",
        "SoftBank took Arm private in 2016; its 2023 re-listing was the year's biggest IPO.",
    ],
    "MU": [
        "Micron was founded in 1978 in the basement of a dental office in Boise, Idaho.",
        "Micron's early backers included J.R. Simplot, the potato magnate who supplied McDonald's fries.",
        "Micron is the last major U.S.-based maker of memory chips.",
    ],
    "STX": [
        "Seagate's first hard drive (1980) held 5 megabytes and cost $1,500.",
        "Seagate was co-founded by Al Shugart — the 'ST' in its early product names stood for Shugart Technology.",
    ],
    "WDC": [
        "Western Digital started in 1970 as a maker of calculator chips.",
        "Western Digital's HDD lineage includes buying IBM's hard drive business (via HGST) in 2012.",
    ],
    "LRCX": [
        "Lam Research was founded in 1980 by physicist David Lam, who emigrated from China via Hong Kong.",
        "Lam's machines etch the microscopic circuits on virtually every advanced chip made today.",
    ],
    "TSM": [
        "TSMC founder Morris Chang started the company in 1987 — at age 55, after a full career at Texas Instruments.",
        "TSMC invented the 'pure-play foundry' model: it only makes chips designed by others.",
        "TSMC manufactures roughly 90% of the world's most advanced chips.",
    ],
    "ASML": [
        "ASML is the only company on Earth that makes EUV lithography machines — each costs over $150 million.",
        "One ASML EUV machine ships in 40 freight containers.",
        "ASML started in 1984 in a leaky shed next to a Philips building in Eindhoven.",
    ],
    "AVGO": [
        "Broadcom's ticker is AVGO because Avago Technologies bought Broadcom in 2016 and kept the better-known name.",
        "Avago's roots trace back to Hewlett-Packard's semiconductor division.",
    ],
    "ORCL": [
        "Oracle is named after a CIA database project codenamed 'Oracle' that Larry Ellison worked on.",
        "Larry Ellison dropped out of college twice before co-founding Oracle in 1977.",
    ],
    "IBM": [
        "IBM is nicknamed 'Big Blue' and topped the U.S. patent list for 29 straight years.",
        "IBM's famous one-word slogan 'THINK' dates back to 1911.",
        "IBM researchers have won six Nobel Prizes.",
    ],
    "LLY": [
        "Eli Lilly was founded in 1876 by Colonel Eli Lilly, a Civil War veteran and pharmacist.",
        "Lilly was the first company to mass-produce insulin (1923) and the Salk polio vaccine.",
    ],
    "NVO": [
        "Novo Nordisk's market value has at times exceeded Denmark's entire annual GDP.",
        "Novo Nordisk is controlled by a charitable foundation — one of the world's largest.",
    ],
    "MELI": [
        "MercadoLibre — 'Latin America's Amazon' — was founded in a Buenos Aires garage in 1999.",
        "Founder Marcos Galperin pitched MercadoLibre while still at Stanford business school.",
    ],
    "DUOL": [
        "Duolingo founder Luis von Ahn co-invented CAPTCHA — and reCAPTCHA, which digitized old books.",
        "Duolingo's pushy owl mascot is named Duo.",
    ],
}

GENERIC_TRIVIA = [
    # --- Origins & history ---
    "The NYSE began in 1792 when 24 brokers signed the Buttonwood Agreement under a buttonwood tree on Wall Street.",
    "The Dutch East India Company issued the world's first publicly traded shares in 1602.",
    "The oldest surviving share certificate — Dutch East India Company, 1606 — was rediscovered by a history student in 2010.",
    "During the 1637 tulip mania, rare bulbs reportedly traded for the price of an Amsterdam canal house.",
    "Short selling was first banned in 1610, after Dutch merchant Isaac Le Maire organized a bear raid on East India Company stock.",
    "Wall Street is named after an actual wall Dutch colonists built across lower Manhattan in the 1650s.",
    "The Bank of New York was the first company listed on the NYSE.",
    "The London Stock Exchange grew out of 17th-century coffee houses where brokers met to trade.",
    "The Bombay Stock Exchange (1875) is the oldest stock exchange in Asia.",
    "The original Dow Jones Industrial Average (1896) had just 12 stocks; General Electric, the last original member, left in 2018.",
    "Charles Dow, of Dow Jones fame, also co-founded The Wall Street Journal.",
    "The Nasdaq, launched in 1971, was the world's first electronic stock market.",
    "U.S. stocks were priced in eighths — a legacy of Spanish 'pieces of eight' — until decimalization in 2001.",
    "The stock ticker got its name from the ticking sound of Edward Calahan's 1867 ticker-tape machine.",
    "Before ticker tape, messengers called 'pad shovers' literally ran stock quotes between Wall Street offices.",
    "The NYSE used a Chinese gong to open and close trading until 1903, when the brass bell arrived.",
    "The SEC was created in 1934; its first chairman was Joseph P. Kennedy, JFK's father.",
    "The word 'stock' comes from the old English word for a tree trunk or block of wood.",
    "The term 'bull market' may come from bulls attacking by thrusting their horns upward.",
    "'Bear market' likely comes from an old proverb about selling the bearskin before catching the bear.",
    "'Blue chip' comes from poker, where blue chips were traditionally the highest-value chips.",
    "Penny-stock quotes were once printed on pink paper — which is why they're still called 'pink sheets'.",
    "Pork bellies were traded on the Chicago Mercantile Exchange until 2011.",
    # --- Crashes & closures ---
    "The worst single-day crash in history was Black Monday (Oct 19, 1987) — down 22.6%.",
    "After the 1929 crash, the Dow kept falling until 1932 — down about 89% from its peak.",
    "The Dow didn't reclaim its 1929 high until 1954 — a 25-year round trip.",
    "The NYSE closed for about four months at the start of World War I in 1914 — its longest shutdown ever.",
    "After 9/11, U.S. markets closed for four trading days — the longest closure since the Great Depression.",
    "Hurricane Sandy closed the market for two days in 2012 — the first multi-day weather closure since the Blizzard of 1888.",
    "The COVID crash of 2020 was the shortest bear market on record — about one month.",
    "The longest bull market in U.S. history ran almost 11 years, from March 2009 to February 2020.",
    "In the 2010 Flash Crash, about $1 trillion in value vanished in minutes — and Accenture briefly traded for a penny.",
    "Knight Capital lost $440 million in 45 minutes in 2012 thanks to a software bug — and was sold within months.",
    "Japan's Nikkei peaked in 1989 and didn't see that level again until 2024 — a 34-year wait.",
    # --- How markets work ---
    "The regular U.S. trading day is just 6.5 hours, and a year has only about 252 trading days.",
    "By most estimates, well over half of U.S. stock trading volume is executed by algorithms.",
    "The S&P 500 actually contains about 503 stocks — some companies list multiple share classes.",
    "The S&P 500 represents roughly 80% of the total U.S. stock market's value.",
    "By some counts there are more stock market indexes than there are U.S. stocks.",
    "The number of U.S. public companies has roughly halved since its 1996 peak.",
    "Single-letter tickers are prized on the NYSE — Ford has held 'F' and AT&T 'T' for around a century.",
    "'Triple witching' — when stock options, index options, and futures all expire at once — hits four Fridays a year.",
    "The VIX volatility index is nicknamed Wall Street's 'fear gauge'.",
    "The Tokyo Stock Exchange still closes for a lunch break every trading day.",
    "Ringing the NYSE bell is a coveted PR moment — guests have included Olympians, astronauts, and Darth Vader.",
    # --- Patterns & superstitions ---
    "September — not October — has historically been the worst month for stocks.",
    "The 'Santa Claus rally': stocks have historically tended to rise in the final days of the year.",
    "The 'January effect' — small stocks outperforming in January — faded soon after researchers publicized it.",
    "The 'Super Bowl indicator' says NFC wins predict up markets — right surprisingly often, by pure coincidence.",
    "Leonard Lauder's 'lipstick index' claims lipstick sales rise in recessions as shoppers trade down to small luxuries.",
    # --- Investing wisdom ---
    "The U.S. stock market has returned about 10% per year on average since 1926, before inflation.",
    "The S&P 500 has had a positive annual return in about 73% of years since 1926.",
    "Historically, the S&P 500 has never lost money over any 20-year holding period.",
    "Studies show missing just the 10 best market days dramatically cuts long-term returns — and they tend to come right after the worst days.",
    "By many estimates, dividends account for roughly a third of the stock market's long-run total return.",
    "Over 90% of day traders lose money, according to academic studies.",
    "Warren Buffett bought his first stock at age 11 — Cities Service Preferred — and later joked he started too late.",
    "Buffett bet $1 million that an index fund would beat a basket of hedge funds over a decade. The index won easily.",
    "Jack Bogle's first index fund (1976) was mocked as 'Bogle's Folly' and even called 'un-American'.",
    "A single share of Coca-Cola's 1919 IPO, with dividends reinvested, would be worth millions today.",
    "More than half of American adults own stocks, whether directly or through retirement accounts.",
]


def ticker_trivia(ticker: str, rng: random.Random | None = None) -> str | None:
    """One fact about *ticker* chosen by the visitor's session RNG; None if no entry."""
    facts = STOCK_TRIVIA.get(ticker)
    if not facts:
        return None
    return (rng or random).choice(facts)


def generic_trivia(rng: random.Random | None = None, count: int = 1) -> list[str]:
    """*count* distinct market facts chosen by the visitor's session RNG."""
    return (rng or random).sample(GENERIC_TRIVIA, min(count, len(GENERIC_TRIVIA)))
