//@tag: general
using System;
using System.Collections.Generic;
using MessagePack;

namespace Corpus;

[Union(0, typeof(Circle))]
[Union(1, typeof(Square))]
public interface IShape { }

[MessagePackObject]
public class Circle : IShape { [Key(0)] public double Radius { get; set; } }

[MessagePackObject]
public class Square : IShape { [Key(0)] public double Side { get; set; } }
