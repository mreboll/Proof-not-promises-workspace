//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Cached
{
    [Key(0)] public string? Value { get; set; }
    [IgnoreMember] public int CacheHits { get; set; }
}
