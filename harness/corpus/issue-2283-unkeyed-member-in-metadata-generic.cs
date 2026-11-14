//@tag: issue-2283
//@library
using MessagePack;

namespace Lib
{
    [MessagePackObject]
    public struct Wrapper<T>
    {
        [Key(0)] public T Content { get; set; }
        public int Unkeyed { get; set; }
    }
}
//@main
using MessagePack;
using Lib;

namespace App
{
    [MessagePackObject]
    public class Holder
    {
        [Key(0)] public Wrapper<int> Value { get; set; }
    }

    [GeneratedMessagePackResolver]
    partial class AppResolver { }
}
