"""Diagnose what tree-sitter actually produces on a known file."""
from tree_sitter import Language, Parser
import tree_sitter_python

# Setup
language = Language(tree_sitter_python.language())
parser = Parser(language)

# Parse a known file with functions
with open("app/api/routes/capabilities.py", "rb") as f:
    content = f.read()

tree = parser.parse(content)
root = tree.root_node

print("=== ROOT NODE TYPE ===")
print(root.type)

print("\n=== TOP LEVEL CHILDREN (first 10) ===")
for child in root.children[:10]:
    print(f"  type={child.type}, text={child.text[:80]}")

print("\n=== FUNCTION NODES (walking full tree) ===")
def walk(node, depth=0):
    if node.type in ("function_definition", "decorated_definition"):
        print(f"  {'  '*depth}[{node.type}] line={node.start_point[0]+1} text={node.text[:60]}")
    for child in node.children:
        walk(child, depth+1)

walk(root)

print("\n=== TEST QUERY: function_definition ===")
try:
    q = language.query("(function_definition name: (identifier) @name)")
    captures = q.captures(root)
    print(f"  captures type: {type(captures)}")
    print(f"  captures: {captures}")
    if isinstance(captures, dict):
        for key, nodes in captures.items():
            print(f"  key={key}, nodes={[n.text.decode() for n in nodes[:5]]}")
    elif isinstance(captures, list):
        for node, name in captures[:5]:
            print(f"  name={name}, text={node.text.decode()}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== TEST QUERY: import_statement ===")
try:
    q = language.query("(import_statement) @imp")
    captures = q.captures(root)
    print(f"  captures type: {type(captures)}")
    if isinstance(captures, dict):
        for key, nodes in captures.items():
            for n in nodes[:3]:
                print(f"  import text: {n.text.decode()[:80]}")
    elif isinstance(captures, list):
        for node, name in captures[:3]:
            print(f"  import text: {node.text.decode()[:80]}")
except Exception as e:
    print(f"  ERROR: {e}")
