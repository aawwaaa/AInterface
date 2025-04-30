class ProviderMetaclass:
    providers = {}

    def __new__(cls, name, bases, attrs):
        instance = type(name, bases, attrs)
        ProviderMetaclass.providers[attrs["name"]] = instance
        return instance
