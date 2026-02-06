# mutmut_config.py

#do_not_mutate = [
#        "src/pysolitaire/dealing.py",
#        "src/pysolitaire/ui_blessed.py",
#]

paths_to_mutate = [
        "src/pysolitaire/rules.py",
]

def pre_mutation(context):
    # Ensure src is importable
    import sys
    if "src" not in sys.path:
        sys.path.insert(0, "src")
