import sys
from pathlib import Path
from zipfile import ZipFile
from tempfile import TemporaryDirectory
import urllib.request as request
import urllib.parse as urlparse
import shutil
import json
from itertools import count
from math import floor, ceil

STEAM = Path("C:/Program Files (x86)/Steam/steamapps/common/Kerbal Space Program/GameData")
STEAM_64 = Path("C:/Program Files/Steam/steamapps/common/Kerbal Space Program/GameData")

def prompt(text, default=True):
    """
    Displays a confirmation prompt with the specified text.
    """
    if default:
        return input(text + " [y]/n: ").lower() in ("y", "yes", "")
    else:
        return input(text + " y/[n]: ") in ("n", "no", "")

def get_folder():
    """
    Determines KSP installation location. Defaults to Steam install, otherwise
    prompts for a location.
    """
    loc = None
    if STEAM.is_dir():
        loc = STEAM
    elif STEAM_64.is_dir():
        loc = STEAM_64
    
    if loc:
        if prompt(f"Found KSP GameData at {loc}, install?"):
            return loc
    
    return Path(input("Enter KSP GameData Location:\n"))

def get_dir(loc):
    """
    Gives a Path object representing the mod folder, and a temporary directory
    to be cleaned up if the mod comes from a zip or is downoaded.
    """
    ploc = Path(loc)
    try:
        if ploc.is_dir():
            return (ploc, None)
    except: pass

    temp = TemporaryDirectory()
    if ploc.suffix == ".zip":
        ziploc = loc
        name = ploc.stem
    elif loc[:3] == "http://:":
        name = "mod"
        ziploc = Path(temp.name, name + ".zip")
        download(loc, ziploc)
    elif loc[:3] == "sd:":
        mod = json.load(request.urlopen("https://spacedock.info/api/mod/" + loc[3:]))
        name = mod["name"]
        if prompt(f"Install {name}?"):
            ziploc = Path(temp.name, name + ".zip")
            download("https://spacedock.info" + mod["versions"][0]["download_path"], ziploc)
        else:
            temp.cleanup()
            sys.exit()
    elif loc[:4] == "sds:":
        mods = json.load(request.urlopen("https://spacedock.info/api/search/mod?query=" + urlparse.quote(loc[4:])))
        print(f"Found {len(mods)} mods:")
        if not mods:
            temp.cleanup()
            sys.exit()
        for i, mod in enumerate(mods):
            print(f"[{i}]: {mod['name']}: {mod['short_description']} ({mod['author']})")
        n = input()
        if n in ("n", "N", ""):
            temp.cleanup()
            sys.exit()
        else:
            mod = mods[int(n)]
            name = mod["name"]
            ziploc = Path(temp.name, name + ".zip")
            download("https://spacedock.info" + mod["versions"][0]["download_path"], ziploc)
    elif loc[:3] == "gh:":
        comps = loc[3:].split("/")
        if len(comps) == 3:
            name = comps[1]
            ziploc = Path(temp.name, name + ".zip")
            download(f"https://github.com/{comps[0]}/{comps[1]}/archive/{comps[2]}.zip", ziploc)
        elif len(comps) == 2:
            mod = json.load(request.urlopen(f"https://api.github.com/repos/{comps[0]}/{comps[1]}/releases"))
            name = mod[0]["assets"][0]["name"]
            ziploc = Path(temp.name, name + ".zip")
            download(mod[0]["assets"][0]["browser_download_url"], ziploc)
        else:
            print(f"Invalid repo!")
            temp.cleanup()
            sys.exit()
    else:
        print(f"{loc} not found!")
        temp.cleanup()
        sys.exit()
    print("Unzipping...")
    with ZipFile(ziploc) as zfil:
        zfil.extractall(Path(temp.name, name))
    return Path(temp.name), temp

def download(url, loc, chunk=16*1024):
    print(f"Downloading {url}, ", end="")
    with request.urlopen(url) as res:
        size = int(res.info()['Content-Length'])
        print(f"{size // 1024:,}kb...")
        with open(loc, "wb") as zipf:
            for i in count():
                frac = i*chunk / size
                print(f"\r{frac*100:6.2f}% [{'-'*ceil(frac*69)}{' '*floor((1-frac)*69)}]", end="")
                buf = res.read(chunk)
                if not buf:
                    print(f"\r100.00% [{'-'*70}]")
                    break
                zipf.write(buf)

def find_gamedata(mod):
    """
    Determines GameData location in mod directory
    """
    datas = list(mod.rglob("GameData/"))
    if len(datas) == 0:
        if prompt(f"Couldn't find GameData, use directory root?"):
            return [mod]
    elif len(datas) == 1:
        if prompt(f"Found GameData at {datas[0].relative_to(mod)}, use?"):
            return [datas[0]]
    else:
        print("Found multiple GameDatas, choose one, or 'a' to use all:")
        for i, gd in enumerate(datas):
            print(f"[{i}]: {gd.relative_to(mod)}")
        ds = input()
        if ds in ("n", "N", ""):
            return []
        if ds in ("a", "A"):
            return datas
        elif ds:
            return [datas[int(i)] for i in ds]
    
    return [mod / input("Enter GameData location in mod directory:\n")]

def install(src, dest):
    for f in src.iterdir():
        dpath = dest / f.name
        print(f.name)
        if dpath.is_dir():
            shutil.rmtree(dpath)
        elif dpath.exists():
            dpath.unlink()
        f.rename(dpath)

def main():
    ksp = get_folder()
    print(f"installing to {ksp}...\n")
    if len(sys.argv) > 1:
        mod_locs = sys.argv[1:]
    else:
        mod_locs = [input("Choose mod location: ")]
        print()
    for i, mod_loc in enumerate(mod_locs):
        print(f"Installing mod {(i+1)}/{len(mod_locs)}: {mod_loc}")
        mod_dir, temp = get_dir(mod_loc)
        print()
        datas = find_gamedata(mod_dir)
        print()
        for d in datas:
            print(f"Installing from {d.relative_to(mod_dir)} ...")
            install(d, ksp)
        if temp:
            temp.cleanup()
        print()
    print("Done!")

if __name__ == "__main__":
    main()