//@tag: issue-2234
using MessagePack;

namespace Corpus;

[MessagePackObject(SuppressSourceGeneration = true)]
public class NoKey
{
    [Key(0)] public int A { get; set; }
    public int Missing { get; set; }
}
