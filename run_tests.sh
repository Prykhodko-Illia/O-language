#!/usr/bin/env bash
# Runs every program in tests/ok and tests/err and compares the result with its .expected:
#   - tests/ok/NAME.txt must compile; the program is run with lli, and its whole output --
#     the lines of air_out, a scat line, a runtime error line -- must match NAME.expected.
#     A program that reads input keeps it in NAME.in, its standard input; without one it
#     reads nothing;
#   - tests/err/NAME.txt must fail -- in the lexer, the parser or the semantic pass -- with
#     a non-zero exit code; its error line must match NAME.expected, and no output file
#     may be written.
# When a NAME.ast file exists next to a program, the --ast dump must match it too; a
# NAME.ast-checked file is the same for --ast-checked, the tree after the semantic pass.
# Usage (with the llvmlite venv active):  ./run_tests.sh

cd "$(dirname "$0")" || exit 2
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

passed=0
failed=0

fail() {
    failed=$((failed + 1))
    echo "FAIL  $1"
    shift
    for line in "$@"; do echo "      $line"; done
}

for src in tests/ok/*.txt tests/err/*.txt; do
    name=${src%.txt}
    case "$src" in
        tests/ok/*) must_compile=true ;;
        *)          must_compile=false ;;
    esac

    if [ ! -f "$name.expected" ]; then
        fail "$name" "no .expected file"
        continue
    fi

    rm -f "$tmp/out.ll"
    if python3 compiler.py "$src" "$tmp/out.ll" 2>"$tmp/stderr"; then
        $must_compile || { fail "$name" "it compiled, but it is in tests/err"; continue; }
        input=/dev/null
        [ -f "$name.in" ] && input="$name.in"
        actual=$(lli "$tmp/out.ll" < "$input" 2>&1)
    else
        $must_compile && { fail "$name" "it failed, but it is in tests/ok" "$(cat "$tmp/stderr")"; continue; }
        [ -f "$tmp/out.ll" ] && { fail "$name" "it failed but still wrote an output file"; continue; }
        actual=$(cat "$tmp/stderr")
    fi

    if [ "$actual" != "$(cat "$name.expected")" ]; then
        fail "$name" "differs from $name.expected:" "$(diff <(echo "$actual") "$name.expected")"
        continue
    fi
    if [ -f "$name.ast" ] && [ "$(python3 compiler.py --ast "$src" 2>&1)" != "$(cat "$name.ast")" ]; then
        fail "$name" "the --ast dump differs from $name.ast:" \
             "$(diff <(python3 compiler.py --ast "$src" 2>&1) "$name.ast")"
        continue
    fi
    if [ -f "$name.ast-checked" ] && [ "$(python3 compiler.py --ast-checked "$src" 2>&1)" != "$(cat "$name.ast-checked")" ]; then
        fail "$name" "the --ast-checked dump differs from $name.ast-checked:" \
             "$(diff <(python3 compiler.py --ast-checked "$src" 2>&1) "$name.ast-checked")"
        continue
    fi

    passed=$((passed + 1))
    echo "PASS  $name"
done

echo
echo "$passed passed, $failed failed"
[ "$failed" -eq 0 ]
