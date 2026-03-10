# Test Programs for SOL26 Interpreter

Simple SOL26 programs for testing your interpreter implementation.

## Programs

### 01-simple-print.sol
**What it does**: Assigns 42 to variable x and prints it

**Expected output**: `42`

**Concepts tested**:
- Variable assignment
- Integer literal
- Message send (print)

**Run**:
```bash
cd python/int
.venv/bin/python src/solint.py --source ../../programs/01-simple-print.xml
```

---

### 02-arithmetic.sol
**What it does**: Adds 5 + 3 and prints the result

**Expected output**: `8`

**Concepts tested**:
- Multiple variable assignments
- Integer literals
- Arithmetic message (plus:)
- Message send (print)

**Run**:
```bash
cd python/int
.venv/bin/python src/solint.py --source ../../programs/02-arithmetic.xml
```

---

### 03-method-call.sol
**What it does**: Defines a `double:` method that doubles a number, calls it with 21, and prints result

**Expected output**: `42`

**Concepts tested**:
- Method definition with parameter
- Method call (self double: 21)
- Parameter access
- Return value from method

**Run**:
```bash
cd python/int
.venv/bin/python src/solint.py --source ../../programs/03-method-call.xml
```

---

## Using with Makefile

```bash
cd python/int
make run ARGS='--source ../../programs/01-simple-print.xml'
make run ARGS='--source ../../programs/02-arithmetic.xml'
make run ARGS='--source ../../programs/03-method-call.xml'
```

## Creating New Test Programs

1. Write SOL code in `programs/mytest.sol`
2. Convert to XML:
   ```bash
   cd sol2xml
   python sol_to_xml.py ../programs/mytest.sol > ../programs/mytest.xml
   ```
3. Run:
   ```bash
   cd python/int
   make run ARGS='--source ../../programs/mytest.xml'
   ```

## SOL26 Quick Reference

**Basic syntax**:
```sol
class Main : Object {
  run
    [ |
      x := 42.          # Assignment
      y := x plus: 1.   # Message send with argument
      _ := y print.     # Print (discard result with _)
    ]
  
  myMethod:           # Method with 1 parameter
    [ :param |
      r := param plus: 10.
    ]
}
```

**Built-in message selectors**:
- Integer: `plus:`, `minus:`, `times:`, `divide:`, `modulo:`, `lessThan:`, `greaterThan:`, `equals:`, etc.
- String: `concat:`, `length`, `asInteger`, etc.
- All: `print`, `asString`, `class`, etc.
- Boolean: `ifTrue:ifFalse:`, `ifTrue:`, `ifFalse:`, `and:`, `or:`, `not`
