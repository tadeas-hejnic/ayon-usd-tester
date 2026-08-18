from pxr import Ar
from usdAssetResolver import AyonUsdResolver

Ar.SetPreferredResolver("AyonUsdResolver")

ctx = AyonUsdResolver.ResolverContext()
resolver = Ar.GetResolver()

source_path = "ayon+entity://dev_project_1//sh010?product=modelTest&version=v001&representation=usd"
target_path = "/home/ynput/dev/ayon-usd-resolver/testAssets/Cone.usd"

ctx.AddMappingPair(source_path, target_path)

with Ar.ResolverContextBinder(ctx):
    resolved_path = resolver.Resolve(source_path)

print(resolved_path)

ctx.RemoveMappingByKey(source_path)

with Ar.ResolverContextBinder(ctx):
    resolved_path_after_removal = resolver.Resolve(source_path)

print(resolved_path_after_removal)
