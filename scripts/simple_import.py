from pxr import Ar
from usdAssetResolver import AyonUsdResolver

Ar.SetPreferredResolver("AyonUsdResolver")

ctx = AyonUsdResolver.ResolverContext()
resolver = Ar.GetResolver()
