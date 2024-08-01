import urllib.request
import json
import re
from bs4 import BeautifulSoup
from sys import argv

url_base = "http://darksouls.wikidot.com"
weapons = { '_types': [], 'full_list': [] }

# ----- Utils -----

def make_req (url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        req = urllib.request.Request(url, headers=headers)
        page = urllib.request.urlopen(req)
        # print("Successfully opened the URL.")
        return page
    except urllib.error.HTTPError as e:
        print(f"HTTP error: {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        print(f"Failed to open URL: {e}")


def read_val(value):
    if value == "–" or value == "-":
        return None
    if '%' in value:
        return read_val(value.replace('%', ''))
    
    try: return int(value.replace(',', ''))
    except ValueError: pass
    try: return float(value.replace(',', ''))
    except ValueError: pass
            
    return value

def get_text(soup_list, separator):
    return separator.join(map(lambda x: x.get_text(), soup_list))

def print_err(str):
    print('\033[45m' + str + "\033[0m")

def clean_str(str):
    return str.replace('\n', ' ')

def get_table_data(elem):
    words = elem.get_text()
    if words != "":
        return words
    child = elem.contents[0]
    if child.name == 'img':
        return child["src"]
    return None

def digest_table(table_headings, table_data):
    headings = map(lambda th: th.get_text(), table_headings.find_all('th'))
    data = map(lambda td: get_table_data(td), table_data.find_all('td'))
    return dict(zip(headings, data))

def get_all_text_upto_elem(elem_start, end_tag):
    following_text = []

    for sibling in elem_start.next_siblings:
        if sibling.name == end_tag:
            break
        next_text = sibling.get_text()
        if next_text != "": following_text.append(next_text)

    # Remove breaks and only break at \n
    return list(filter(len, "".join(following_text).split("\n")))

def stats_breakdown(str, stat_type):
    keys = {
        'damage': ['physical', 'magic', 'fire', 'lightning'],
        'stats': ['strength', 'dexterity', 'intelligence', 'faith'],
        'aux_effects': ['bleed', 'poison', 'divine', 'occult'],
    }

    stats = list(map(read_val, str.split("/")))
    return dict(zip(keys[stat_type], stats))

# ----- Scrapers -----

def scrape_weapon(name, href, weap_type):
    print("\tScraping weapon: " + name + " -- " + href)

    weapon = {
        'name': name,
        'href': href,
        'weapon_type': weap_type,
    }

    weapon_page = make_req(weapon['href'])
    weapon_soup = BeautifulSoup(weapon_page, 'html.parser')

    # Remove all footnotes
    for sup in weapon_soup.find_all('sup'):
        sup.decompose()

    # Description, Availability, Other Information

    desc = weapon_soup.find('h2', string="In-Game Description")
    if desc is None:
        desc = weapon_soup.find('h2', string="In Game Description")

    if desc is not None:
        weapon['description'] = clean_str(desc.find_next_sibling().getText())
    else:
        print_err('NO DESCRIPTION FOR ' + name)
        weapon['description'] = None

    avail = weapon_soup.find('h2', string="Availability")
    weapon['availability'] = get_all_text_upto_elem(avail, 'h2')

    info = weapon_soup.find('h2', string="General Information")
    after_info = info.find_next_sibling()

    if after_info.name == 'div' or after_info.name == 'p':
        weapon['info'] = get_all_text_upto_elem(info, 'table')
    elif after_info.name == 'table':
        weapon['info'] = None
    else:
        print_err(name + " info err")

    # Tabled base stats

    table_headings = weapon_soup.find('th', string="Image").parent
    table_data = table_headings.find_next_sibling()

    gen_stats = digest_table(table_headings, table_data)

    weapon['image'] = gen_stats['Image']
    del gen_stats['Image']

    def pop_gen_stat(key_js, key_html):
        if key_html in gen_stats:
            weapon[key_js] = read_val(gen_stats[key_html])
            del gen_stats[key_html]
        else:
            weapon[key_js] = None

    pop_gen_stat('critical', 'Critical')
    pop_gen_stat('durability', 'Durability')
    pop_gen_stat('weight', 'Weight')
    pop_gen_stat('stability', 'Stability')
    pop_gen_stat('frampt_souls', 'Frampt Souls')
    pop_gen_stat('frampt_souls', 'Frampt\nSouls')

    if "\n\n" in gen_stats['Damage']:
        damage_parts = gen_stats['Damage'].split("\n\n")
    elif "\n" in gen_stats['Damage']:
        damage_parts = gen_stats['Damage'].split("\n")
    else:
        damage_parts = []
    
    if len(damage_parts) == 3:
        damage, effects, damage_type = damage_parts
    elif len(damage_parts) == 2:
        damage, damage_type = damage_parts
        effects = None
    else:
        damage, effects, damage_type = [gen_stats['Damage'], None, None]

    if damage_type != None:
        damage_type = damage_type.replace("(", "").replace(")", "")
    
    weapon['damage_type'] = damage_type
    weapon['damage_effects'] = effects
    weapon['damage'] = [ stats_breakdown(damage, 'damage') ]
    del gen_stats['Damage']

    if "Stats Needed\nStat Bonuses" in gen_stats:
        if '\n\n' in gen_stats["Stats Needed\nStat Bonuses"]:
            stats_req, stats_bonus = gen_stats["Stats Needed\nStat Bonuses"].split('\n\n')
        elif '\n' in gen_stats["Stats Needed\nStat Bonuses"]:
            stats_req, stats_bonus = gen_stats["Stats Needed\nStat Bonuses"].split('\n')
        else:
            print_err('ohnooo we got stats problems on ' + name)
            stats_req, stats_bonus = ["",""]
        
        weapon['stats_required'] = stats_breakdown(stats_req, 'stats')
        weapon['stats_bonus'] = [ stats_breakdown(stats_bonus, 'stats') ]
        del gen_stats["Stats Needed\nStat Bonuses"]
            
    else:
        weapon['stats_required'] = None
        weapon['stats_bonus'] = None

    if 'Damage\nReduction %' in gen_stats:
        weapon['damage_reduction'] = stats_breakdown(gen_stats["Damage\nReduction %"], 'damage')
        del gen_stats['Damage\nReduction %']
    elif 'Damage Reduction %' in gen_stats:
        weapon['damage_reduction'] = stats_breakdown(gen_stats["Damage Reduction %"], 'damage')
        del gen_stats['Damage Reduction %']
    elif 'Damage Reduction' in gen_stats:
        weapon['damage_reduction'] = stats_breakdown(gen_stats["Damage Reduction"], 'damage')
        del gen_stats['Damage Reduction']
    else:
        weapon['damage_reduction'] = stats_breakdown('-/-/-/-', 'damage')
    
    if 'Aux Effects' in gen_stats:
        weapon['auxillary_effects'] = stats_breakdown(gen_stats["Aux Effects"], 'aux_effects')
        del gen_stats["Aux Effects"]
    else:
        weapon['auxillary_effects'] = stats_breakdown('-/-/-/-', 'aux_effects')

    if 'Critical Bonus' in gen_stats:
        weapon['critical_bonus'] = read_val(gen_stats['Critical Bonus'])
        del gen_stats['Critical Bonus']
    elif 'Critical\nBonus' in gen_stats:
        weapon['critical_bonus'] = read_val(gen_stats['Critical\nBonus'])
        del gen_stats['Critical\nBonus']
    else:
        weapon['critical_bonus']: None

    if 'Range' in gen_stats:
        weapon['range'] = read_val(gen_stats['Range'])
        del gen_stats['Range']

    del gen_stats['Name']
    if len(gen_stats):
        print_err('More stats present in ' + name + ' - need to deal with the following:')
        print(gen_stats)

    #  Upgrade Info
    

    # # Upgrades
    # upgrades = {}
    # upgrades_containers = weapon_soup.select('div.weapon_details_upgrade_container div.detailstable')
    # for upgrade_container in upgrades_containers:
    #     upgrade_name = upgrade_container.h4.span.attrs['id']
    #     rows = upgrade_container.table.select('tr')
    #     upgrade = {}
    #     for row in rows:
    #         data = row.contents
    #         plus_val = data[0].contents[0]
    #         upgrade[plus_val] = {}
    #         damage = {}
    #         damage_reduction = {}
    #         bonus = {}

    #         damage['physical'] = read_val(data[1].contents[0])
    #         damage['magic'] = read_val(data[2].contents[0])
    #         damage['fire'] = read_val(data[3].contents[0])
    #         damage['lightning'] = read_val(data[4].contents[0])

    #         damage_reduction['physical'] = read_val(data[5].contents[0])
    #         damage_reduction['magic'] = read_val(data[6].contents[0])
    #         damage_reduction['fire'] = read_val(data[7].contents[0])
    #         damage_reduction['lightning'] = read_val(data[8].contents[0])

    #         bonus['strength'] = read_val(data[9].contents[0])
    #         bonus['dexterity'] = read_val(data[10].contents[0])
    #         bonus['intelligence'] = read_val(data[11].contents[0])
    #         bonus['faith'] = read_val(data[12].contents[0])

    #         upgrade[plus_val]['damage'] = damage
    #         upgrade[plus_val]['damage_reduction'] = damage_reduction
    #         upgrade[plus_val]['bonus'] = bonus

    #     upgrades[upgrade_name] = upgrade

    # weapon['upgrades'] = upgrades
    return weapon
        
def scrape_weapon_list(filename):
    page = make_req(url_base + "/weapons")
    soup = BeautifulSoup(page, 'html.parser')

    weapon_div = soup.find('h2', string="All Weapons by Type").parent
    all_types = weapon_div.find_all('h3')

    for type_heading in all_types:
        type_title = type_heading.string
        weapons['_types'].append(type_title) 

        weap_list = type_heading.find_next_sibling().find_all('a')
        for weap_tag in weap_list:
            name = weap_tag.string
            link = url_base + weap_tag['href']
            total_weapon = scrape_weapon(name, link, type_title)
            weapons['full_list'].append(total_weapon)

if __name__ == "__main__":
    print("Init scraping")

    if len(argv) < 2:
        print("Usage: " + argv[0] + " OUTPUT_FILE")
        exit(1)

    scrape_weapon_list(argv[1])
    
    with open('weapons.json', 'w', encoding='utf-8') as json_file:
        json.dump(weapons, json_file, indent=2)

    # print(weapons)
    print("Finished scraping")
    exit(0)
