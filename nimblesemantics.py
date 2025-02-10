"""
Group members: TODO: your names

Version: TODO: completion date

TODO: read this description, implement to make it true.

The nimblesemantics module contains classes sufficient to perform a semantic analysis
of Nimble programs.

The analysis has two major tasks:

- to infer the types of all expressions in a Nimble program and to add appropriate type
annotations to the program's ANTLR-generated syntax tree by storing an entry in the `node_types`
dictionary for each expression node, where the key is the node and the value is a
`symboltable.PrimitiveType` or `symboltable.FunctionType`.

- to identify and flag all violations of the Nimble semantic specification
using the `errorlog.ErrorLog` and other classes in the `errorlog` module.

There are two phases to the analysis:

1. DefineScopesAndSymbols, and

2. InferTypesAndCheckSemantics.

In the first phase, `symboltable.Scope` objects are created for all scope-defining parse
tree nodes: the script, each function definition, and the main. These are stored in the
`self.scopes` dictionary. Also in this phase, all declared function types must be recorded
in the appropriate scope.

Parameter and variable types can be recorded in the appropriate scope in either the first
phase or the second phase.

In the second phase, type inference is performed and all other semantic constraints are
checked.

"""

from errorlog import ErrorLog, Category
from nimble import NimbleListener, NimbleParser
from symboltable import PrimitiveType, Scope


class DefineScopesAndSymbols(NimbleListener):

    def __init__(self, error_log: ErrorLog, global_scope: Scope, types: dict):
        self.error_log = error_log
        self.current_scope = global_scope
        self.type_of = types

    def enterMain(self, ctx: NimbleParser.MainContext):
        self.current_scope = self.current_scope.create_child_scope('$main', PrimitiveType.Void)

    def exitMain(self, ctx: NimbleParser.MainContext):
        self.current_scope = self.current_scope.enclosing_scope


class InferTypesAndCheckConstraints(NimbleListener):
    """
    The type of each expression parse tree node is calculated and stored in the
    `self.type_of` dictionary, where the key is the node object, and the value is
    an instance of `symboltable.PrimitiveType`.

    The types of declared variables are stored in `self.variables`, which is a dictionary
    mapping from variable names to `symboltable.PrimitiveType` instances.

    Any semantic errors detected, e.g., undefined variable names,
    type mismatches, etc., are logged in the `error_log`
    """

    def __init__(self, error_log: ErrorLog, global_scope: Scope, types: dict):
        self.error_log = error_log
        self.current_scope = global_scope
        self.type_of = types

    # --------------------------------------------------------
    # Program structure
    # --------------------------------------------------------

    def exitScript(self, ctx: NimbleParser.ScriptContext):
        pass

    def enterMain(self, ctx: NimbleParser.MainContext):
        self.current_scope = self.current_scope.child_scope_named('$main')

    def exitMain(self, ctx: NimbleParser.MainContext):
        self.current_scope = self.current_scope.enclosing_scope

    def exitBody(self, ctx: NimbleParser.BodyContext):
        pass

    def exitVarBlock(self, ctx: NimbleParser.VarBlockContext):
        pass

    def exitBlock(self, ctx: NimbleParser.BlockContext):
        pass

    # --------------------------------------------------------
    # Variable declarations
    # --------------------------------------------------------

    def exitVarDec(self, ctx: NimbleParser.VarDecContext):

        if ctx.TYPE().getText() == "Int":
            self.current_scope.define(ctx.ID().getText(), PrimitiveType.Int)
        elif ctx.TYPE().getText() == "String":
            self.current_scope.define(ctx.ID().getText(), PrimitiveType.String)
        elif ctx.TYPE().getText() == "Bool":
            self.current_scope.define(ctx.ID().getText(), PrimitiveType.Bool)
        else:
            self.error_log.add(ctx, Category.INVALID_NEGATION,
                               f"{self.type_of[ctx].name} is invalid type name")
            return
        if ctx.expr():
            if self.type_of[ctx]!=self.type_of[ctx.expr()]:
                self.error_log.add(ctx, Category.INVALID_NEGATION,
                                       f"cannot assign {ctx.expr().getText()} to type {ctx.TYPE().getText()}")
                self.type_of[ctx] = PrimitiveType.ERROR
        #add resolve locally


    # --------------------------------------------------------
    # Statements
    # --------------------------------------------------------

    def exitAssignment(self, ctx: NimbleParser.AssignmentContext):
        #is x declared
        #is x declared as a variable
        pass

    def exitWhile(self, ctx: NimbleParser.WhileContext):
        pass

    def exitIf(self, ctx: NimbleParser.IfContext):
        pass

    def exitPrint(self, ctx: NimbleParser.PrintContext):
        pass

    # --------------------------------------------------------
    # Expressions
    # --------------------------------------------------------

    def exitIntLiteral(self, ctx: NimbleParser.IntLiteralContext):
        self.type_of[ctx] = PrimitiveType.Int

    def exitNeg(self, ctx: NimbleParser.NegContext):
        """ TODO: Extend to handle boolean negation. """
        if ctx.op.text == '-' and self.type_of[ctx.expr()] == PrimitiveType.Int:
            self.type_of[ctx] = PrimitiveType.Int
        elif ctx.op.text == '!' and self.type_of[ctx.expr()] == PrimitiveType.Bool:
            self.type_of[ctx] = PrimitiveType.Bool
        else:
            self.type_of[ctx] = PrimitiveType.ERROR
            self.error_log.add(ctx, Category.INVALID_NEGATION,
                               f"Can't apply {ctx.op.text} to {self.type_of[ctx].name}")

    def exitParens(self, ctx: NimbleParser.ParensContext):
        self.type_of[ctx] = self.type_of[ctx.expr()]

    def exitMulDiv(self, ctx: NimbleParser.MulDivContext):
        if self.type_of[ctx.expr(0)] == PrimitiveType.Int and self.type_of[ctx.expr(1)] == PrimitiveType.Int and (
                ctx.op.text == '*' or ctx.op.text == '/'):
            self.type_of[ctx] = PrimitiveType.Int
        else:
            self.type_of[ctx] = PrimitiveType.ERROR
            self.error_log.add(ctx, Category.INVALID_BINARY_OP,
                               f'cant mul or div {ctx.expr(0)} and {ctx.expr(1)} together')

    def exitAddSub(self, ctx: NimbleParser.AddSubContext):
        if self.type_of[ctx.expr(0)] == PrimitiveType.Int and self.type_of[ctx.expr(1)] == PrimitiveType.Int and (
                ctx.op.text == '+' or ctx.op.text == ('-')):
            self.type_of[ctx] = PrimitiveType.Int
        elif self.type_of[ctx.expr(0)] == PrimitiveType.String and self.type_of[
            ctx.expr(1)] == PrimitiveType.String and ctx.op.text == '+':
            self.type_of[ctx] = PrimitiveType.String
        else:
            self.type_of[ctx] = PrimitiveType.ERROR
            self.error_log.add(ctx, Category.INVALID_BINARY_OP,
                               f'cant add or sub {ctx.expr(0)} and {ctx.expr(1)} together')

    def exitCompare(self, ctx: NimbleParser.CompareContext):
        #2 op texts, 1 str. both expr must be int, returns bool#
        #1) ==
        if self.type_of[ctx.expr(0)] == PrimitiveType.Bool and self.type_of[
            ctx.expr(1)] == PrimitiveType.Bool and ctx.op.text == '==':
            self.type_of[ctx] = PrimitiveType.Bool
        elif self.type_of[ctx.expr(0)] == PrimitiveType.Int and self.type_of[
            ctx.expr(1)] == PrimitiveType.Int and ctx.op.text == '==':
            self.type_of[ctx] = PrimitiveType.Bool
        elif self.type_of[ctx.expr(0)] == PrimitiveType.Int and self.type_of[
            ctx.expr(1)] == PrimitiveType.Int and ctx.op.text == '<':
            self.type_of[ctx] = PrimitiveType.Bool
        elif self.type_of[ctx.expr(0)] == PrimitiveType.Int and self.type_of[
            ctx.expr(1)] == PrimitiveType.Int and ctx.op.text == '<=':
            self.type_of[ctx] = PrimitiveType.Bool
        else:
            self.type_of[ctx] = PrimitiveType.ERROR
            self.error_log.add(ctx, Category.INVALID_BINARY_OP, F"Can't do a binary operation with types:"
                                                                F"{ctx.expr(0).getText()}, {ctx.expr(1).getText()} and operation: {ctx.op.text}")

    def exitVariable(self, ctx: NimbleParser.VariableContext):
        #resolve on scope with variable name.
        #check the current scope for the variable symbol
        if not self.current_scope.resolve_locally(ctx.getText()):
            self.type_of[ctx] = PrimitiveType.ERROR
            self.error_log.add(ctx, Category.UNDEFINED_NAME, F"{ctx.getText()} is undefined")
            return

        #Find the type of the variable
        self.type_of[ctx] = self.current_scope.resolve(ctx.getText()).PrimitiveType



    def exitStringLiteral(self, ctx: NimbleParser.StringLiteralContext):
        self.type_of[ctx] = PrimitiveType.String

    def exitBoolLiteral(self, ctx: NimbleParser.BoolLiteralContext):
        self.type_of[ctx] = PrimitiveType.Bool
