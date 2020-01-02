from typing import Callable, Dict, Any, Tuple, List
import catalogue
import inspect
from pydantic import create_model
from pydantic.main import ModelMetaclass


class _PromiseSchemaConfig:
    extra = "forbid"


class registry(object):
    """Function registries that map string keys to objects."""

    optimizers = catalogue.create("thinc", "optimizers", entry_points=True)
    schedules = catalogue.create("thinc", "schedules", entry_points=True)
    layers = catalogue.create("thinc", "layers", entry_points=True)

    @classmethod
    def create(cls, registry_name: str, entry_points: bool = False) -> None:
        """Create a new custom registry."""
        if hasattr(cls, registry_name):
            raise ValueError(f"Registry '{registry_name}' already exists")
        reg = catalogue.create("thinc", registry_name, entry_points=entry_points)
        setattr(cls, registry_name, reg)

    @classmethod
    def get(cls, registry_name: str, func_name: str) -> Callable:
        """Get a registered function from a given registry."""
        if not hasattr(cls, registry_name):
            raise ValueError(f"Unknown registry: '{registry_name}'")
        reg = getattr(cls, registry_name)
        func = reg.get(func_name)
        if func is None:
            raise ValueError(f"Could not find '{func_name}' in '{registry_name}'")
        return func

    @classmethod
    def make_from_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Unpack a config dictionary, creating objects from the registry
        recursively.
        """
        # TODO: rewrite and merge with fill_and_validate
        # Recurse over subdictionaries, filling in values.
        filled = {}
        for key, value in config.items():
            if isinstance(value, dict):
                filled[key] = cls.make_from_config(value)
            else:
                filled[key] = value
        if cls.is_promise(filled):
            getter = cls.get_constructor(filled)
            args, kwargs = cls.parse_args(filled)
            return getter(*args, **kwargs)
        else:
            return filled

    @classmethod
    def fill_and_validate(cls, config, schema):
        """Build two representations of the config: one where the promises are
        preserved, and a second where the promises are represented by their
        return types. Use the validation representation to get default
        values via pydantic. The defaults are filled into both representations.
        """
        # TODO: custom validation errors
        filled = {}
        validation = {}
        for key, value in config.items():
            if cls.is_promise(value):
                promise_schema = cls.make_promise_schema(value)
                filled[key], _ = cls.fill_and_validate(value, promise_schema)
                type_ = cls.get_return_type(value)
                validation[key] = type_.__new__(type_)
            elif hasattr(value, "items"):
                field = schema.__fields__[key]
                filled[key], validation[key] = cls.fill_and_validate(value, field.type_)
            else:
                filled[key] = value
                validation[key] = value
        # Now that we've filled in all of the promises, update with defaults
        # from schema, and validate.
        validation.update(schema.parse_obj(validation).dict())
        for key, value in validation.items():
            if key not in filled:
                filled[key] = value
        return filled, validation

    @classmethod
    def is_promise(cls, obj: Any) -> bool:
        if not hasattr(obj, "keys"):
            return False
        id_keys = [k for k in obj.keys() if k.startswith("@")]
        if len(id_keys) != 1:
            return False
        else:
            return True

    @classmethod
    def get_constructor(cls, obj: Dict[str, Any]) -> Callable:
        id_keys = [k for k in obj.keys() if k.startswith("@")]
        if len(id_keys) != 1:
            raise ValueError
        else:
            key = id_keys[0]
            value = obj[key]
            return cls.get(key[1:], value)

    @classmethod
    def parse_args(cls, obj: Dict[str, Any]) -> Tuple[List[Any], Dict[str, Any]]:
        args = []
        kwargs = {}
        for key, value in obj.items():
            if not key.startswith("@"):
                if isinstance(key, int) or key.isdigit():
                    args.append((int(key), value))
                else:
                    kwargs[key] = value
        return [value for key, value in sorted(args)], kwargs

    @classmethod
    def make_promise_schema(cls, obj: Dict[str, Any]) -> ModelMetaclass:
        func = cls.get_constructor(obj)
        # Read the argument annotations and defaults from the function signature
        id_keys = [k for k in obj.keys() if k.startswith("@")]
        sig_args: Dict[str, Any] = {id_keys[0]: (str, ...)}
        for param in inspect.signature(func).parameters.values():
            # If no default value is specified assume that it's required
            if param.default != param.empty:
                sig_args[param.name] = (param.annotation, param.default)
            else:
                sig_args[param.name] = (param.annotation, ...)
        sig_args["__config__"] = _PromiseSchemaConfig
        return create_model("ArgModel", **sig_args)

    @classmethod
    def get_return_type(cls, obj: Dict[str, Any]):
        func = cls.get_constructor(obj)
        return inspect.signature(func).return_annotation
