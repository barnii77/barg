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

$builtin.int(Int);

Recovery := ".*?;\\s*\\n*\\s*";  # smart recovery pattern (what to skip if no match)

Expr := Int | Var;  # tests union composition syntax sugar

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

        mg = barg.parse((test_source,), test_grammar, "Toplevel")[0]
        m = next(mg)[0]
        self.assertTrue(isinstance(m, list))
        self.assertEqual(len(m), 4)
        self.assertEqual(m[0].var.name, "name")
        self.assertEqual(m[0].expr.value, 1)
        self.assertEqual(m[1].var.name, "second_var")
        self.assertEqual(m[1].expr.name, "name")
        self.assertEqual(m[2].var.name, "third_var")
        self.assertEqual(m[2].expr.value, 256)
        self.assertEqual(m[3].var.name, "v4")
        self.assertEqual(m[3].expr.name, "second_var")


if __name__ == "__main__":
    unittest.main()
