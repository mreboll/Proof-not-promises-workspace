//@tag: issue-2234
using MessagePack;

namespace Corpus;

[MessagePackObject(SuppressSourceGeneration = true)]
public class Mixed
{
    [Key(0)] public int A { get; set; }
    [Key("b")] public int B { get; set; }
}
