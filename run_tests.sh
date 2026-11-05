#!/usr/bin/env bash
# Runs every program in tests/ok, tests/err, tests/opt and programs/ and compares the
# result with its .expected:
#   - tests/ok/NAME.txt must compile; the program is run with lli, and its whole output --
#     the lines of air_out, a scat line, a runtime error line -- must match NAME.expected.
#     A program that reads input keeps it in NAME.in, its standard input; without one it
#     reads nothing;
#   - tests/err/NAME.txt must fail -- in the lexer, the parser or the semantic pass -- with
#     a non-zero exit code; its error line must match NAME.expected, and no output file
#     may be written;
#   - every program of tests/ok and tests/err is then compiled again with --optimize, and
#     must give the same output, or the same error, as without it;
#   - tests/opt/NAME.txt is a test of the optimizer: it is run with and without
#     --optimize, both outputs must match NAME.expected, and the tree after
#     --optimize --ast must match NAME.ast;
#   - programs/NAME.txt is a whole program, with recorded sessions: programs/NAME.in (and
#     NAME.2.in, NAME.3.in, ...) is what the user types, NAME.expected (NAME.2.expected,
#     ...) the exact output. It is built into a native binary with llc and clang -- with
#     and without --optimize -- and each session is run on both binaries. Where llc or
#     clang is missing, the sessions run with lli instead, and the script says so.
# When a NAME.ast file exists next to a program of tests/ok or tests/err, the --ast dump
# must match it too; a NAME.ast-checked file is the same for --ast-checked, the tree after
# the semantic pass.
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

# compile FLAGS... SRC: compiles SRC into $tmp/out.ll and sets $actual to the program's
# output (run with lli on NAME.in) or to the error line. Returns 0 when it compiled.
compile_and_run() {
    local src=$1 name=${1%.txt}
    shift
    rm -f "$tmp/out.ll"
    if python3 compiler.py "$@" "$src" "$tmp/out.ll" 2>"$tmp/stderr"; then
        local input=/dev/null
        [ -f "$name.in" ] && input="$name.in"
        actual=$(lli "$tmp/out.ll" < "$input" 2>&1)
        return 0
    fi
    actual=$(cat "$tmp/stderr")
    return 1
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

    ok=true
    for flag in "" --optimize; do                  # the same result with and without it
        label="$name${flag:+ $flag}"
        if compile_and_run "$src" $flag; then
            $must_compile || { fail "$label" "it compiled, but it is in tests/err"; ok=false; break; }
        else
            $must_compile && { fail "$label" "it failed, but it is in tests/ok" "$actual"; ok=false; break; }
            [ -f "$tmp/out.ll" ] && { fail "$label" "it failed but still wrote an output file"; ok=false; break; }
        fi
        if [ "$actual" != "$(cat "$name.expected")" ]; then
            fail "$label" "differs from $name.expected:" "$(diff <(echo "$actual") "$name.expected")"
            ok=false
            break
        fi
    done
    $ok || continue
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

for src in tests/opt/*.txt; do
    name=${src%.txt}
    if [ ! -f "$name.expected" ] || [ ! -f "$name.ast" ]; then
        fail "$name" "a test of the optimizer needs a .expected and a .ast file"
        continue
    fi
    ok=true
    for flag in "" --optimize; do
        label="$name${flag:+ $flag}"
        if ! compile_and_run "$src" $flag; then
            fail "$label" "it failed to compile" "$actual"
            ok=false
            break
        fi
        if [ "$actual" != "$(cat "$name.expected")" ]; then
            fail "$label" "differs from $name.expected:" "$(diff <(echo "$actual") "$name.expected")"
            ok=false
            break
        fi
    done
    $ok || continue
    tree=$(python3 compiler.py --optimize --ast "$src" 2>&1)
    if [ "$tree" != "$(cat "$name.ast")" ]; then
        fail "$name" "the tree after --optimize --ast differs from $name.ast:" \
             "$(diff <(echo "$tree") "$name.ast")"
        continue
    fi
    passed=$((passed + 1))
    echo "PASS  $name"
done

native=true
if ! command -v llc >/dev/null || ! command -v clang >/dev/null; then
    native=false
    echo "NOTE  no llc or clang here: the sessions of programs/ run with lli"
fi
for src in programs/*.txt; do
    [ -e "$src" ] || continue
    name=${src%.txt}
    ok=true
    for flag in "" --optimize; do
        label="$name${flag:+ $flag}"
        rm -f "$tmp/prog.ll" "$tmp/prog.o" "$tmp/prog"
        if ! python3 compiler.py $flag "$src" "$tmp/prog.ll" 2>"$tmp/stderr"; then
            fail "$label" "it failed to compile" "$(cat "$tmp/stderr")"
            ok=false
            break
        fi
        if $native && ! { llc -filetype=obj -relocation-model=pic "$tmp/prog.ll" -o "$tmp/prog.o" &&
                          clang -fPIE "$tmp/prog.o" -o "$tmp/prog"; } 2>"$tmp/stderr"; then
            fail "$label" "llc or clang failed" "$(cat "$tmp/stderr")"
            ok=false
            break
        fi
        sessions=0
        for input in "$name".in "$name".*.in; do
            [ -f "$input" ] || continue
            sessions=$((sessions + 1))
            expected=${input%.in}.expected
            if $native; then
                actual=$("$tmp/prog" < "$input" 2>&1)
            else
                actual=$(lli "$tmp/prog.ll" < "$input" 2>&1)
            fi
            if [ "$actual" != "$(cat "$expected" 2>/dev/null)" ]; then
                fail "$label < $input" "differs from $expected:" "$(diff <(echo "$actual") "$expected")"
                ok=false
            fi
        done
        if [ "$sessions" -lt 2 ]; then
            fail "$name" "a program needs at least two recorded sessions, $name.in and $name.2.in"
            ok=false
        fi
        $ok || break
    done
    $ok || continue
    passed=$((passed + 1))
    echo "PASS  $name ($sessions sessions, $($native && echo "native binary" || echo "lli"))"
done

echo
echo "$passed passed, $failed failed"
[ "$failed" -eq 0 ]
