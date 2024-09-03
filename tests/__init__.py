import unittest
import barg


class Exec(unittest.TestCase):
    def test1(self):
        test_grammar = """\
Int := struct {
    value: $builtin.int("[0-9]+")
};

Var := struct {
    name: "[a-zA-Z_][a-zA-Z0-9_]*"
};

$builtin.int(\"\"\"\\d+\"\"\");

Recovery := ".*?;\\s*\\n*\\s*";  # smart recovery pattern (what to skip if no match)

# tests union composition syntax sugar and the pyscript builtin
Expr := $builtin.pyscript(Int | Var, ```
if x.type_ == barg.GenTyKind.STRUCT:
    x._PYSCRIPT_RAN_SUCCESSFULLY = True
else:
    raise Exception("matched pattern is not of type struct")
```);

# marks as ok if match was found for non-recovery pattern
Assignment := $builtin.mark(struct {
    var: Var,
    "\\s*=\\s*",
    expr: Expr,
    ";" "\\s*(\\n)*\\s*",  # tests sequence composition syntax sugar
}, ok) | Recovery;

# filters out those matches that were not ok (skipped parts due to recovery)
Toplevel := $builtin.filter(Assignment*, ok);  # filter out the matches of recovery pattern
"""

        # note the error on line 3, `name 245`: it is recovered from using the smart recovery mechanism
        test_source = """\
name = 1;
second_var = name;
name 245;
third_var = 256;
v4 = second_var;
"""

        errs = []
        out = barg.parse((test_source,), test_grammar, errs, "Toplevel")
        self.assertEqual(1, len(out))
        self.assertNotIsInstance(out[0], Exception)
        assert not isinstance(out[0], Exception)
        mg = out[0]
        self.assertEqual(0, len(errs))
        m = next(mg)[0]
        self.assertTrue(isinstance(m, list))
        self.assertEqual(4, len(m))
        self.assertEqual("name", m[0].var.name)
        self.assertEqual(1, m[0].expr.value)
        self.assertEqual("second_var", m[1].var.name)
        self.assertEqual("name", m[1].expr.name)
        self.assertEqual("third_var", m[2].var.name)
        self.assertEqual(256, m[2].expr.value)
        self.assertEqual("v4", m[3].var.name)
        self.assertEqual("second_var", m[3].expr.name)
        for stmt in m:
            self.assertTrue(hasattr(stmt.expr, "_PYSCRIPT_RAN_SUCCESSFULLY"))
            self.assertTrue(stmt.expr._PYSCRIPT_RAN_SUCCESSFULLY)

    def test2(self):
        test_grammar = """\
Int := struct {
    value: $builtin.int("\\d+")
};

Var := struct {
    name: "[a-zA-Z_][a-zA-Z0-9_]*"
};

$builtin.int(\"\"\"\\d+\"\"\");

Recovery := ".*?;\\s*\\n*\\s*";  # smart recovery pattern (what to skip if no match)

# you can also assign text strings to variables if you need to apply python code multiple times (to reduce repetition)
PyCode := ```
if x.type_ == barg.GenTyKind.STRUCT:
    x._PYSCRIPT_RAN_SUCCESSFULLY = True
else:
    raise Exception("matched pattern is not of type struct")
```;

# tests union composition syntax sugar and the pyscript builtin
Expr := $builtin.pyscript(Int | Var, PyCode);

# marks as ok if match was found for non-recovery pattern
Equals := "\\s*=\\s*";

Assignment := $builtin.mark(struct {
    var: Var,
    Equals,
    expr: Expr,
    ";" "\\s*(\\n)*\\s*",  # tests sequence composition syntax sugar
}, ok) | Recovery;

# filters out those matches that were not ok (skipped parts due to recovery)
Toplevel := $builtin.filter(Assignment*, ok);  # filter out the matches of recovery pattern
"""

        # note the error on line 3, `name 245`: it is recovered from using the smart recovery mechanism
        test_source = """\
name = 1;
second_var = name;
name 245;
third_var = 256;
v4 = second_var;
"""

        errs = []
        out = barg.parse((test_source,), test_grammar, errs, "Toplevel")
        self.assertEqual(1, len(out))
        self.assertNotIsInstance(out[0], Exception)
        assert not isinstance(out[0], Exception)
        mg = out[0]
        self.assertEqual(0, len(errs))
        m = next(mg)[0]
        self.assertTrue(isinstance(m, list))
        self.assertEqual(4, len(m))
        self.assertEqual("name", m[0].var.name)
        self.assertEqual(1, m[0].expr.value)
        self.assertEqual("second_var", m[1].var.name)
        self.assertEqual("name", m[1].expr.name)
        self.assertEqual("third_var", m[2].var.name)
        self.assertEqual(256, m[2].expr.value)
        self.assertEqual("v4", m[3].var.name)
        self.assertEqual("second_var", m[3].expr.name)
        for stmt in m:
            self.assertTrue(hasattr(stmt.expr, "_PYSCRIPT_RAN_SUCCESSFULLY"))
            self.assertTrue(stmt.expr._PYSCRIPT_RAN_SUCCESSFULLY)


if __name__ == "__main__":
    unittest.main()
