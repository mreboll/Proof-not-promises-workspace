//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Animal
{
    [Key(0)] public string? Name { get; set; }
}

[MessagePackObject]
public class Dog : Animal
{
    [Key(1)] public bool GoodBoy { get; set; }
}
