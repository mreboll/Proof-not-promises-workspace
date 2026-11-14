//@tag: general
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Person
{
    [Key(0)] public int Id { get; set; }
    [Key(1)] public string? Name { get; set; }
    [Key(2)] public double Score { get; set; }
}
