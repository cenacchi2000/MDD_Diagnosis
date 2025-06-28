import types
import typing
from inspect import getfullargspec

from docstring_parser import parse


def get_functions_prompt_map(
    functions: typing.Iterable[typing.Callable] | typing.Callable,
):
    # Duck typing - allow for list of functions or a single function
    if not isinstance(functions, typing.Iterable):
        functions = [functions]

    def get_arg_schema(type_: type) -> str:
        if type_ == str:
            return {"type": "string"}
        elif type_ == int:
            return {"type": "integer"}
        elif type_ == float:
            return {"type": "number"}
        # Handle type literals for enums
        elif type(type_) is typing._LiteralGenericAlias:
            types_ = set([type(t) for t in typing.get_args(type_)])
            if len(types_) > 1:
                raise Exception("Literal with inconsistent types: ", types_)
            elif len(types_) == 0:
                raise Exception("Empty literal: ", types_)
            else:
                ret = get_arg_schema(types_.pop())
                ret["enum"] = list(typing.get_args(type_))
                return ret

        elif type(type_) is typing.GenericAlias and type_.__origin__ == tuple:
            # Leaving the code in below, in case it is supported in the future, but it doesn't look like openai supports tuples
            raise NotImplementedError(
                "OpenAI does not seem to support arguments as tuples"
            )
            items = [{"type": get_arg_schema(element)} for element in type_.__args__]
            return {"type": "array", "items": items}
        elif type(type_) is typing.GenericAlias and type_.__origin__ == list:
            types_ = set([t for t in type_.__args__])
            if len(types_) > 1:
                raise Exception("List with inconsistent types: ", types_)

            sub_type = get_arg_schema(types_.pop())
            return {"type": "array", "items": {"type": sub_type["type"]}}
        elif type(type_) is typing._UnionGenericAlias:
            types_ = set([t for t in typing.get_args(type_) if t is not types.NoneType])
            if len(types_) > 1:
                raise Exception(
                    f"Unions are not supported in types. Found a union with types: {typing.get_args(type_)}"
                )
            else:
                return get_arg_schema(types_.pop())
        else:
            return {"type": str(type_)}

    ret = {}
    for fun in functions:
        dp = parse(fun.__doc__)

        function_description = dp.short_description
        long_description = (
            dp.long_description.replace("#REQUIRES_SUBSEQUENT_FUNCTION_CALLS", "")
            if dp.long_description is not None
            else ""
        )
        if len(long_description) > 0:
            function_description += "\n" + long_description

        arg_names, _, _, defaults, _, _, annotations = getfullargspec(fun)

        if defaults is None:
            defaults = []
        defaults_by_arg = {
            arg_name: str(default)
            for arg_name, default in zip(arg_names[-1::-1], defaults[-1::-1])
        }
        parameters = {
            "type": "object",
            "properties": {},
            "required": arg_names[: -len(defaults)] if len(defaults) > 0 else arg_names,
        }
        for arg in dp.params:
            if arg.arg_name[0] != "_" and arg.arg_name != "self":
                arg_schema = get_arg_schema(annotations[arg.arg_name])
                description = arg.description
                if (default := defaults_by_arg.get(arg.arg_name)) is not None:
                    description += f" Defaults to {default}."
                arg_schema["description"] = description
                parameters["properties"][arg.arg_name] = arg_schema

        function_name = fun.__name__
        prompt = {
            "name": function_name,
            "description": function_description,
            "parameters": parameters,
        }
        ret[function_name] = {
            "function": fun,
            "prompt": prompt,
            "requires_subsequent_function_calls": dp.long_description is not None
            and "#REQUIRES_SUBSEQUENT_FUNCTION_CALLS" in dp.long_description,
        }
    return ret