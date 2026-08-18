from pxr import Ar
from usdAssetResolver import AyonUsdResolver

Ar.SetPreferredResolver("AyonUsdResolver")
resolver = Ar.GetResolver()
context = AyonUsdResolver.ResolverContext()

resolved_path = resolver.Resolve("ayon+entity://project/asset/variant/representation")

print(f"Resolved path: {resolved_path}")
