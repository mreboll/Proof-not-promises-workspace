//@tag: general
using MessagePack;

namespace Corpus;

[MessagePackObject]
public class Constrained<T> where T : class, new()
{
    [Key(0)] public T? Value { get; set; }
}

[MessagePackObject]
public class UsesConstrained
{
    [Key(0)] public Constrained<object>? Item { get; set; }
}
