import subprocess


def run(command):
    print(f"\n> {command}")
    result = subprocess.run(command, shell=True)

    if result.returncode != 0:
        print("\n❌ Something went wrong.")
        exit(1)


print("================================")
print("   CODEFORCES TRACKER SYNC")
print("================================")

run("git add .")

run('git commit -m "Update tracker"')

run("git push")

print("\n✓ Your tracker has been uploaded!")
print("✓ GitHub Pages will update shortly.")