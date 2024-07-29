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
    if value == "–":
        return None
    elif '%' in value:
        return read_val(value.replace('%', ''))
    elif '.' in value:
        return float(value)
    elif value.isnumeric():
        return int(value)
    else:
        return value

def get_text(soup_list, separator):
    return separator.join(map(lambda x: x.get_text(), soup_list))

def print_err(str):
    print('\033[45m' + str + "\033[0m")

def clean_str(str):
    return str.replace('\n', ' ')

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

    # Description, Availability, Other Information

    desc = weapon_soup.find('h2', string="In-Game Description")
    if desc is None:
        desc = desc = weapon_soup.find('h2', string="In Game Description")

    if desc is not None:
        weapon['description'] = clean_str(desc.find_next_sibling().getText())
    else:
        print_err('NO DESCRIPTION FOR ' + name)
        weapon['description'] = ""

    avail = weapon_soup.find('h2', string="Availability")
    weapon['availability'] = avail.find_next_sibling().getText()

    info = weapon_soup.find('h2', string="General Information")
    after_info = info.find_next_sibling()
    if after_info.name == 'div' or after_info.name == 'p':
        weapon['info'] = after_info.getText()
    elif after_info.name == 'table':
        weapon['info'] = ""
    else:
        print_err(name + " info err")

    # Tabled base info


    #  Upgrade Info
    
    # # Weight, Stability, Durability, Critical
    # fourth_containers = weapon_soup.select('div.fourth.container')
    # for container in fourth_containers:
    #     stat = container.h3.contents[0]
    #     weapon[stat] = read_val(container.find('span', class_='num').contents[0])

    # # Damage, Damage Reduction, Requirements, Auxiliary, Bonus
    # third_containers = weapon_soup.select('div.third.container')
    # damage_type_container = third_containers.pop()
    # for container in third_containers:
    #     stat_type = container.h3.contents[0].replace(' ', '_')
    #     if stat_type == 'reduction':
    #         stat_type = 'damage_reduction'
    #     stats = container.find_all('span', class_='')
    #     weapon[stat_type] = {}
    #     for stat in stats:
    #         stat_name = stat.contents[0]
    #         if stat_name == 'normal':
    #             stat_name = 'physical'
    #         sibling = stat.find_previous_sibling('span', class_='num')
    #         weapon[stat_type][stat_name] = read_val(sibling.contents[0])

    # # Attack Type
    # attack_types = damage_type_container.find_all('span', class_='num')
    # attack_types_ok = filter(lambda x: int(re.findall('\d+', x.attrs['style'])[0]) > 1, attack_types)
    # attack_types_desc = map(lambda x: x.find_next_sibling('span', class_=''), attack_types_ok)
    # attack_type = get_text(attack_types_desc, '/')
    # weapon['attack_type'] = attack_type

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

    weapon_div = soup.find('h2', string="All Weapons by Type").find_parent('td')
    all_types = weapon_div.find_all('h3')

    for type_heading in all_types:
        type_title = type_heading.get_text()
        weapons['_types'].append(type_title) 

        weap_list = type_heading.find_next_sibling().find_all('a')
        for weap_tag in weap_list:
            name = weap_tag.get_text()
            link = url_base + weap_tag.get('href')
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
