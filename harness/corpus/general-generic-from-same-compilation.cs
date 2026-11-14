//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public struct LocalWrapper<T>
{
    [Key(0)] public T Content { get; set; }
    public int Unkeyed { get; set; }
}

[MessagePackObject]
public class UsesLocal
{
    [Key(0)] public LocalWrapper<int> Value { get; set; }
}
