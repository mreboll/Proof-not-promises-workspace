//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Page<T>
{
    [Key(0)] public List<T>? Items { get; set; }
    [Key(1)] public int Total { get; set; }
}

[MessagePackObject]
public class Catalog
{
    [Key(0)] public Page<string>? Names { get; set; }
    [Key(1)] public Page<int>? Ids { get; set; }
}
