# get_packages.py
import pkg_resources

with open("requirements.txt", encoding="utf-8") as f:
    required = [
        line.strip().split("==")[0]
        for line in f
        if line.strip() and not line.startswith("#")
    ]

print("\nVersions installées :")
for pkg in required:
    try:
        version = pkg_resources.get_distribution(pkg).version
        print(f"{pkg} == {version}")
    except pkg_resources.DistributionNotFound:
        print(f"{pkg} ❌ non installé")

