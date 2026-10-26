#!/usr/bin/env bash
# Runs every program in tests/ok and tests/err and compares the result with its .expected:
#   - tests/ok/NAME.txt must parse and pass the semantic pass; the --ast dump must match
#     NAME.expected;
#   - tests/err/NAME.txt must fail -- in the lexer, the parser or the semantic pass -- with
#     a non-zero exit code, print nothing on stdout, and its error line on stderr must
#     match NAME.expected.
# Usage:  ./run_tests.sh

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
        tests/ok/*) must_parse=true ;;
        *)          must_parse=false ;;
    esac

    if [ ! -f "$name.expected" ]; then
        fail "$name" "no .expected file"
        continue
    fi

    if python3 compiler.py --ast-checked "$src" >"$tmp/stdout" 2>"$tmp/stderr"; then
        $must_parse || { fail "$name" "it compiled, but it is in tests/err"; continue; }
        actual=$(python3 compiler.py --ast "$src")
    else
        $must_parse && { fail "$name" "it failed, but it is in tests/ok" "$(cat "$tmp/stderr")"; continue; }
        [ -s "$tmp/stdout" ] && { fail "$name" "it failed but still printed output"; continue; }
        actual=$(cat "$tmp/stderr")
    fi

    if [ "$actual" != "$(cat "$name.expected")" ]; then
        fail "$name" "differs from $name.expected:" "$(diff <(echo "$actual") "$name.expected")"
        continue
    fi

    passed=$((passed + 1))
    echo "PASS  $name"
done

echo
echo "$passed passed, $failed failed"
[ "$failed" -eq 0 ]
