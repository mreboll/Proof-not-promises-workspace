//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public readonly struct Version3
{
    [SerializationConstructor]
    public Version3(int major, int minor, int patch)
    {
        Major = major;
        Minor = minor;
        Patch = patch;
    }

    [Key(0)] public int Major { get; }
    [Key(1)] public int Minor { get; }
    [Key(2)] public int Patch { get; }
}
