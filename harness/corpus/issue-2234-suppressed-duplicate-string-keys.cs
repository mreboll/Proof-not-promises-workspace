//@tag: issue-2234
using MessagePack;

namespace Corpus;

[MessagePackObject(SuppressSourceGeneration = true)]
public class DupString
{
    [Key("x")] public int A { get; set; }
    [Key("x")] public int B { get; set; }
}
